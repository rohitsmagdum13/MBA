"""
Monolithic CLI for MBA data ingestion to S3 with duplicate detection.

This module provides the main command-line interface for the MBA ingestion system,
supporting both monolithic and microservices modes of operation. It handles file
discovery, duplicate detection, and batch uploads to S3 with comprehensive
error handling and progress tracking.

The CLI supports three primary modes:
- monolith: Direct upload with all processing in a single process
- micro: Enqueues jobs for distributed processing via workers
- check-duplicates: Scans for duplicate files without uploading

Key Features:
- Automatic scope detection from file paths (mba/policy)
- Local and S3 duplicate detection with MD5 hashing
- Concurrent uploads with configurable parallelism
- Dry-run mode for testing configurations
- Comprehensive audit logging and error reporting

Usage:
    MBA-ingest --input ./data --auto-detect-scope
    MBA-ingest --mode check-duplicates --input ./data --check-s3
    MBA-ingest --input ./data --scope mba --dry-run

Author: MBA Healthcare Management Associates
Version: 1.0.0
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Optional, List, Tuple
import click

from MBA.agents.orchestration_agent.wrapper import OrchestratorAgent

from MBA.core.settings import settings
from MBA.core.logging_config import get_logger, setup_root_logger
from MBA.core.exceptions import FileDiscoveryError, UploadError, ConfigError
from MBA.services.s3_client import build_session, upload_file
from MBA.services.file_utils import (
    discover_files, 
    parse_extensions, 
    build_s3_key, 
    detect_scope_from_path  # This is the function that was missing
)
from MBA.services.duplicate_detector import DuplicateDetector

logger = get_logger(__name__)


class Uploader:
    """
    Handles file uploads to S3 with duplicate detection.
    
    This class encapsulates the upload logic including duplicate detection,
    retry mechanisms, and progress tracking for batch file uploads.
    
    Attributes:
        scope (Optional[str]): Upload scope ("mba" or "policy")
        dry_run (bool): If True, simulates upload without actual transfer
        auto_detect_scope (bool): If True, detects scope from file path
        skip_duplicates (bool): If True, skips files that already exist
        overwrite (bool): If True, overwrites existing files in S3
        duplicate_detector (DuplicateDetector): Instance for duplicate checking
        bucket (Optional[str]): Target S3 bucket name
        prefix (Optional[str]): S3 key prefix
        session (Optional[boto3.Session]): AWS session for S3 operations
    """
    
    def __init__(
        self,
        scope: Optional[str] = None,
        aws_profile: Optional[str] = None,
        region: Optional[str] = None,
        dry_run: bool = False,
        auto_detect_scope: bool = False,
        skip_duplicates: bool = True,  # New parameter
        overwrite: bool = False  # New parameter
    ):
        """
        Initialize uploader with configuration options.
        
        Args:
            scope: Upload scope ("mba" or "policy"), optional if auto_detect_scope is True
            aws_profile: AWS profile name to use for credentials
            region: AWS region for S3 operations
            dry_run: If True, only simulates uploads without actual transfer
            auto_detect_scope: If True, automatically detects scope from file path
            skip_duplicates: If True, skips files that already exist in S3
            overwrite: If True, overwrites existing files in S3
            
        Raises:
            ConfigError: If scope is invalid when provided
            
        Side Effects:
            - Initializes AWS session if not in dry_run mode
            - Creates DuplicateDetector instance
        """
        self.scope = scope
        self.dry_run = dry_run
        self.auto_detect_scope = auto_detect_scope
        self.skip_duplicates = skip_duplicates
        self.overwrite = overwrite
        
        # Initialize duplicate detector
        self.duplicate_detector = DuplicateDetector()
        
        # If scope is provided, get bucket and prefix
        if scope:
            try:
                self.bucket = settings.get_bucket(scope)
                self.prefix = settings.get_prefix(scope)
            except ValueError as e:
                raise ConfigError(f"Invalid scope: {scope}")
        else:
            self.bucket = None
            self.prefix = None
        
        # Build AWS session (not needed for dry run)
        if not dry_run:
            self.session = build_session(
                profile=aws_profile or settings.aws_profile,
                access_key=settings.aws_access_key_id,
                secret_key=settings.aws_secret_access_key,
                region=region or settings.aws_default_region
            )
        else:
            self.session = None
            
    def upload_single(self, file_path: Path, input_dir: Path) -> Tuple[Path, bool, str]:
        """
        Upload a single file with duplicate checking.
        
        Processes a single file through the upload pipeline including scope
        detection, duplicate checking, and actual upload with retry logic.
        
        Args:
            file_path (Path): Absolute path to file to upload
            input_dir (Path): Base input directory for relative path calculation
            
        Returns:
            Tuple[Path, bool, str]: A tuple containing:
                - Path: The file path that was processed
                - bool: True if successful (uploaded or skipped), False if failed
                - str: Status message describing the outcome
                
        Side Effects:
            - May upload file to S3
            - Logs operation details
            - Updates duplicate detector cache
        """
        # Determine scope for this file
        if self.auto_detect_scope:
            detected_scope = detect_scope_from_path(file_path, input_dir)
            if detected_scope:
                file_scope = detected_scope
                logger.debug(f"Auto-detected scope '{file_scope}' for {file_path.name}")
            else:
                if self.scope:
                    file_scope = self.scope
                    logger.debug(f"Using default scope '{file_scope}' for {file_path.name}")
                else:
                    return (file_path, False, "Could not determine scope for file")
        else:
            file_scope = self.scope
        
        # Get bucket and prefix for this file's scope
        try:
            bucket = settings.get_bucket(file_scope)
            prefix = settings.get_prefix(file_scope)
        except ValueError as e:
            return (file_path, False, f"Invalid scope: {file_scope}")
        
        # Build S3 key
        s3_key = build_s3_key(file_scope, file_path, prefix)
        
        # Check for local duplicates if requested
        if self.skip_duplicates and not self.dry_run:
            # Check for duplicates in the input directory
            local_duplicates = self.duplicate_detector.check_local_duplicate(
                file_path, 
                [input_dir]
            )
            
            if local_duplicates:
                logger.warning(f"File {file_path.name} has {len(local_duplicates)} local duplicates")
                # Continue with upload but log warning
        
        # Dry run - just print what would be done
        if self.dry_run:
            # Check if file exists in S3
            if self.session and self.skip_duplicates:
                from MBA.services.s3_client import check_s3_file_exists
                exists, _ = check_s3_file_exists(self.session, bucket, s3_key)
                
                if exists and not self.overwrite:
                    logger.info(f"[DRY RUN] Would skip (exists): {file_path.relative_to(input_dir)}")
                    return (file_path, True, "Would skip (already exists)")
            
            logger.info(f"[DRY RUN] Would upload: {file_path.relative_to(input_dir)} -> s3://{bucket}/{s3_key}")
            return (file_path, True, f"s3://{bucket}/{s3_key}")
        
        # Actual upload with duplicate checking
        try:
            success, message = upload_file(
                session=self.session,
                bucket=bucket,
                local_path=file_path,
                s3_key=s3_key,
                check_duplicate=self.skip_duplicates,
                overwrite=self.overwrite
            )
            
            if success:
                if message == "Skipped (duplicate)":
                    return (file_path, True, f"Skipped - already in S3: {s3_key}")
                else:
                    return (file_path, True, f"Uploaded to s3://{bucket}/{s3_key}")
            else:
                return (file_path, False, message)
                
        except UploadError as e:
            return (file_path, False, f"Error: {e.message}")
        except Exception as e:
            return (file_path, False, f"Unexpected error: {e}")
            
    def upload_batch(
        self,
        files: List[Path],
        input_dir: Path,
        concurrency: int = 4
    ) -> dict:
        """
        Upload multiple files in parallel with duplicate detection.
        
        Orchestrates parallel upload of multiple files using ThreadPoolExecutor
        for concurrent operations. Includes duplicate scanning before upload.
        
        Args:
            files (List[Path]): List of file paths to upload
            input_dir (Path): Base directory for all files
            concurrency (int): Number of concurrent upload workers
            
        Returns:
            dict: Statistics dictionary containing:
                - total (int): Total number of files processed
                - uploaded (int): Number of successfully uploaded files
                - skipped (int): Number of files skipped (duplicates)
                - failed (int): Number of failed uploads
                - results (List[Tuple]): Detailed results for each file
                
        Side Effects:
            - Uploads files to S3
            - Logs duplicate detection results
            - Updates progress indicators
        """
        uploaded = 0
        skipped = 0
        failed = 0
        results = []
        
        # First, scan for local duplicates if requested
        if self.skip_duplicates:
            logger.info("Scanning for local duplicates...")
            hash_to_files = self.duplicate_detector.scan_local_directory(input_dir)
            
            # Find duplicate groups
            duplicate_groups = {
                h: paths for h, paths in hash_to_files.items() 
                if len(paths) > 1
            }
            
            if duplicate_groups:
                report = self.duplicate_detector.generate_report(duplicate_groups)
                logger.warning(f"\n{report}")
        
        # Use ThreadPoolExecutor for parallel uploads
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit all upload tasks
            futures = {
                executor.submit(self.upload_single, file_path, input_dir): file_path
                for file_path in files
            }
            
            # Process results as they complete
            for future in as_completed(futures):
                file_path = futures[future]
                
                try:
                    path, success, message = future.result()
                    results.append((path, success, message))
                    
                    if success:
                        if "Skipped" in message:
                            skipped += 1
                            logger.info(f"⊘ {path.name}: {message}")
                        else:
                            uploaded += 1
                            logger.info(f"✓ {path.name}: {message}")
                    else:
                        failed += 1
                        logger.error(f"✗ {path.name}: {message}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"✗ {file_path.name}: {e}")
                    results.append((file_path, False, str(e)))
        
        return {
            "total": len(files),
            "uploaded": uploaded,
            "skipped": skipped,
            "failed": failed,
            "results": results
        }


def run_monolith(args: argparse.Namespace) -> int:
    """
    Run monolithic ingestion process with duplicate detection.
    
    Main execution function for monolithic mode, handling the complete
    upload pipeline from file discovery to final statistics reporting.
    
    Args:
        args (argparse.Namespace): Parsed command line arguments containing:
            - input (Path): Input directory to scan
            - scope (Optional[str]): Upload scope
            - include (Optional[str]): Extensions to include
            - exclude (Optional[str]): Extensions to exclude
            - concurrency (int): Number of parallel workers
            - dry_run (bool): Dry run flag
            - auto_detect_scope (bool): Auto-detection flag
            - no_skip_duplicates (bool): Skip duplicate checking
            - overwrite (bool): Overwrite existing files
            - aws_profile (Optional[str]): AWS profile
            - region (Optional[str]): AWS region
            
    Returns:
        int: Exit code (0 for success, 1 for any failures)
        
    Side Effects:
        - Uploads files to S3
        - Prints summary statistics to console
        - Logs all operations
    """
    try:
        # Parse extension filters
        include_exts = parse_extensions(args.include) if args.include else None
        exclude_exts = parse_extensions(args.exclude) if args.exclude else None
        
        # Determine if we should auto-detect scope
        auto_detect = args.auto_detect_scope or args.scope is None
        
        # Discover files
        logger.info(f"Scanning directory: {args.input}")
        
        if args.scope and not auto_detect:
            # Scan within specific scope subdirectory
            files = discover_files(
                input_dir=args.input,
                include_extensions=include_exts,
                exclude_extensions=exclude_exts,
                scope=args.scope
            )
        else:
            # Scan entire directory
            files = discover_files(
                input_dir=args.input,
                include_extensions=include_exts,
                exclude_extensions=exclude_exts
            )
        
        if not files:
            logger.warning("No files found matching criteria")
            return 0
        
        logger.info(f"Found {len(files)} files to process")
        
        # Create uploader with duplicate detection settings
        uploader = Uploader(
            scope=args.scope,
            aws_profile=args.aws_profile,
            region=args.region,
            dry_run=args.dry_run,
            auto_detect_scope=auto_detect,
            skip_duplicates=not args.no_skip_duplicates,  # Note the negation
            overwrite=args.overwrite
        )
        
        # Upload files
        logger.info(f"Starting upload with {args.concurrency} workers...")
        stats = uploader.upload_batch(files, input_dir=args.input, concurrency=args.concurrency)
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"Upload Summary:")
        if args.scope:
            print(f"  Scope: {args.scope}")
        else:
            print(f"  Scope: Auto-detected from path")
        print(f"  Input: {args.input}")
        print(f"  Total files: {stats['total']}")
        print(f"  Uploaded: {stats['uploaded']}")
        print(f"  Skipped (duplicates): {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")
        if stats['total'] > 0:
            success_rate = ((stats['uploaded'] + stats['skipped']) / stats['total']) * 100
            print(f"  Success rate: {success_rate:.1f}%")
        print(f"{'='*50}\n")
        
        # Return exit code based on failures
        return 0 if stats['failed'] == 0 else 1
        
    except (FileDiscoveryError, ConfigError) as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


def run_duplicate_check(args: argparse.Namespace) -> int:
    """
    Run duplicate checking without uploading.
    
    Scans directories for duplicate files using hash comparison and
    optionally checks against existing S3 objects.
    
    Args:
        args (argparse.Namespace): Parsed arguments containing:
            - input (Path): Directory to scan
            - check_s3 (bool): Whether to check S3 for duplicates
            - scope (Optional[str]): Scope for S3 checking
            - aws_profile (Optional[str]): AWS profile
            - region (Optional[str]): AWS region
            
    Returns:
        int: Exit code (0 for success, 1 for errors)
        
    Side Effects:
        - Prints duplicate report to console
        - May query S3 for existing objects
        - Updates duplicate detector cache
    """
    try:
        from MBA.services.duplicate_detector import DuplicateDetector
        
        detector = DuplicateDetector()
        
        # Ensure input path is resolved
        input_dir = Path(args.input).resolve()
        
        # Scan local directory
        logger.info(f"Scanning for duplicates in: {input_dir}")
        hash_to_files = detector.scan_local_directory(input_dir)
        
        # Find duplicates
        duplicates = {
            h: paths for h, paths in hash_to_files.items() 
            if len(paths) > 1
        }
        
        # Generate and print report with base directory
        report = detector.generate_report(duplicates, base_dir=input_dir)
        print(report)
        
        # If checking against S3
        if args.check_s3:
            session = build_session(
                profile=args.aws_profile or settings.aws_profile,
                access_key=settings.aws_access_key_id,
                secret_key=settings.aws_secret_access_key,
                region=args.region or settings.aws_default_region
            )
            
            print("\nChecking against S3...")
            s3_duplicates = 0
            
            for file_path in input_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Detect scope from path
                scope = detect_scope_from_path(file_path, input_dir)
                if not scope:
                    scope = args.scope or "mba"  # Default
                
                # Get bucket and build key
                bucket = settings.get_bucket(scope)
                prefix = settings.get_prefix(scope)
                s3_key = build_s3_key(scope, file_path, prefix)
                
                # Check if exists in S3
                is_dup, metadata = detector.check_s3_duplicate(
                    session, file_path, bucket, s3_key
                )
                
                if is_dup:
                    s3_duplicates += 1
                    relative_path = file_path.relative_to(input_dir)
                    print(f"  S3 duplicate: {relative_path} -> s3://{bucket}/{s3_key}")
            
            print(f"\nFound {s3_duplicates} files already in S3")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during duplicate check: {e}", exc_info=True)
        return 1


def main():
    """
    Main entry point for CLI with duplicate detection.
    
    Parses command line arguments and routes to appropriate execution mode
    (monolith, microservices, or duplicate check).
    
    Input:
        Command line arguments from sys.argv
        
    Output:
        Exit code to operating system
        
    Side Effects:
        - Sets up root logger
        - Executes chosen mode
        - Exits process with appropriate code
    """
    # Set up root logger
    setup_root_logger()
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="MBA Data Ingestion - Upload files to S3 with structured paths and duplicate detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload all files with duplicate detection (default)
  MBA-ingest --input ./data --auto-detect-scope
  
  # Upload and overwrite duplicates
  MBA-ingest --input ./data --auto-detect-scope --overwrite
  
  # Upload without checking duplicates (faster)
  MBA-ingest --input ./data --auto-detect-scope --no-skip-duplicates
  
  # Check for duplicates without uploading
  MBA-ingest --mode check-duplicates --input ./data
  
  # Check local files against S3
  MBA-ingest --mode check-duplicates --input ./data --check-s3
  
  # Dry run to see what would be uploaded
  MBA-ingest --input ./data --auto-detect-scope --dry-run
        """
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["monolith", "micro", "check-duplicates"],
        default="monolith",
        help="Execution mode (default: monolith)"
    )
    
    # Scope argument (optional)
    parser.add_argument(
        "--scope",
        choices=["mba", "policy"],
        help="Upload scope - determines bucket and prefix (optional with --auto-detect-scope)"
    )
    
    # Auto-detect scope from path
    parser.add_argument(
        "--auto-detect-scope",
        action="store_true",
        help="Automatically detect scope from file path (data/mba/* or data/policy/*)"
    )
    
    # Input configuration
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("./data"),
        help="Input directory to scan (default: ./data)"
    )
    
    # Filtering options
    parser.add_argument(
        "--include",
        help="Comma-separated list of extensions to include (e.g., pdf,csv)"
    )
    
    parser.add_argument(
        "--exclude",
        help="Comma-separated list of extensions to exclude"
    )
    
    # Processing options
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of concurrent uploads (default: 4)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be uploaded without actually uploading"
    )
    
    # Duplicate handling
    parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="Upload files even if they already exist in S3"
    )
    
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in S3"
    )
    
    parser.add_argument(
        "--check-s3",
        action="store_true",
        help="Check local files against S3 (only with --mode check-duplicates)"
    )
    
    # AWS configuration
    parser.add_argument(
        "--aws-profile",
        help="AWS profile to use (overrides environment)"
    )
    
    parser.add_argument(
        "--region",
        help="AWS region (overrides environment)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode != "check-duplicates":
        if not args.auto_detect_scope and not args.scope:
            parser.error("Either --scope or --auto-detect-scope must be specified")
    
    if args.check_s3 and args.mode != "check-duplicates":
        parser.error("--check-s3 can only be used with --mode check-duplicates")
    
    if args.overwrite and args.no_skip_duplicates:
        logger.warning("Both --overwrite and --no-skip-duplicates specified; --overwrite takes precedence")
    
    # Log startup
    logger.info(f"MBA Ingestion starting in {args.mode} mode")
    if args.mode != "check-duplicates":
        logger.info(f"Configuration: scope={args.scope if args.scope else 'auto-detect'}, input={args.input}")
        logger.info(f"Duplicate handling: skip={not args.no_skip_duplicates}, overwrite={args.overwrite}")
    
    # Run appropriate mode
    if args.mode == "monolith":
        exit_code = run_monolith(args)
    elif args.mode == "check-duplicates":
        exit_code = run_duplicate_check(args)
    else:
        exit_code = run_microservices(args)
    
    sys.exit(exit_code)


def run_microservices(args: argparse.Namespace) -> int:
    """
    Run in microservices mode (launches producer).
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code
    """
    logger.info("Running in microservices mode - launching producer...")
    
    # Import and run producer
    from MBA.microservices.producer import enqueue_files
    from MBA.microservices.queue import job_queue
    
    try:
        # Parse extension filters
        include_exts = parse_extensions(args.include) if args.include else None
        exclude_exts = parse_extensions(args.exclude) if args.exclude else None
        
        # Enqueue files
        job_count = enqueue_files(
            input_dir=args.input,
            scope=args.scope,
            include_extensions=include_exts,
            exclude_extensions=exclude_exts
        )
        
        # Print instructions
        print(f"\n{'='*50}")
        print(f"Microservices Mode - Jobs Enqueued: {job_count}")
        print(f"\nTo process jobs, run:")
        print(f"  MBA-worker --concurrency {args.concurrency}")
        print(f"\nTo start API server, run:")
        print(f"  MBA-api")
        print(f"{'='*50}\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Producer error: {e}", exc_info=True)
        return 1


# Click CLI group for additional commands
@click.group()
def mba():
    """MBA CLI commands."""
    pass

@mba.command("orchestrate")
@click.option("--query", required=True, help="User question with any member hints")
def orchestrate_cmd(query: str):
    """
    Run the Orchestrator Agent from CLI.
    Example:
      uv run python -m MBA.cli.cli orchestrate --query \
      "What's my deductible for 2025? member_id=123 dob=1990-05-15"
    """
    payload = {"query": query}
    orch = OrchestratorAgent()
    result = asyncio.run(orch.run(payload))
    click.echo(json.dumps(result, indent=2))

@mba.command("verify")
@click.option("--member-id", required=True, help="Member ID")
@click.option("--dob", required=True, help="Date of birth (YYYY-MM-DD)")
@click.option("--name", help="Member name (optional)")
def verify_cmd(member_id: str, dob: str, name: str = None):
    """
    Verify member identity.
    Example:
      uv run python -m MBA.cli.cli verify --member-id M1001 --dob 2005-05-23
    """
    from MBA.agents.member_verification_agent.tools import verify_member
    
    params = {"member_id": member_id, "dob": dob}
    if name:
        params["name"] = name
    
    result = asyncio.run(verify_member(params))
    click.echo(json.dumps(result, indent=2))

@mba.command("intent")
@click.option("--query", required=True, help="User query to analyze")
def intent_cmd(query: str):
    """
    Identify intent from user query.
    Example:
      uv run python -m MBA.cli.cli intent --query "What's my deductible for 2025?"
    """
    from MBA.agents.intent_identification_agent.tools import identify_intent_and_params
    
    result = asyncio.run(identify_intent_and_params(query))
    click.echo(json.dumps(result, indent=2))

@mba.command("benefits")
@click.option("--member-id", required=True, help="Member ID")
@click.option("--service", help="Specific service (optional)")
@click.option("--plan-year", default=2025, help="Plan year (default: 2025)")
def benefits_cmd(member_id: str, service: str = None, plan_year: int = 2025):
    """
    Get benefit accumulator information.
    Example:
      uv run python -m MBA.cli.cli benefits --member-id M1001 --service "Massage Therapy"
    """
    from MBA.agents.benefit_accumulator_agent.tools import get_benefit_details
    
    params = {"member_id": member_id, "plan_year": plan_year}
    if service:
        params["service"] = service
    
    result = asyncio.run(get_benefit_details(params))
    click.echo(json.dumps(result, indent=2))

@mba.command("deductible")
@click.option("--member-id", required=True, help="Member ID")
@click.option("--plan-year", default=2025, help="Plan year (default: 2025)")
def deductible_cmd(member_id: str, plan_year: int = 2025):
    """
    Get deductible and out-of-pocket information.
    Example:
      uv run python -m MBA.cli.cli deductible --member-id M1001 --plan-year 2025
    """
    from MBA.agents.deductible_oop_agent.tools import get_deductible_oop
    
    params = {"member_id": member_id, "plan_year": plan_year}
    result = asyncio.run(get_deductible_oop(params))
    click.echo(json.dumps(result, indent=2))

if __name__ == "__main__":
    # Check if we're being called with click commands
    if len(sys.argv) > 1 and sys.argv[1] in ['orchestrate', 'verify', 'intent', 'benefits', 'deductible']:
        mba()
    else:
        main()
