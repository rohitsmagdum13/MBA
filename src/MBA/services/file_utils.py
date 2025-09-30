"""
File discovery and processing utilities.

Provides filesystem scanning, type detection, and S3 key generation
utilities for the ingestion pipeline.

Module Input:
    - Directory paths to scan
    - File paths for analysis
    - Extension filters
    - Scope identifiers

Module Output:
    - Lists of discovered files
    - File type categories
    - S3 key strings
    - Scope detection results
"""

from pathlib import Path
from typing import List, Set, Optional

from ..core.logging_config import get_logger
from ..core.exceptions import FileDiscoveryError

# Initialize logger for this module
logger = get_logger(__name__)

# File type mapping: extension -> category
FILE_TYPE_MAPPING = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".tiff": "image",
    ".csv": "csv",
    ".json": "json",
    ".txt": "text",
    ".log": "text",
    ".md": "text",
    ".docx": "docx",
    ".doc": "docx",
    ".xlsx": "excel",
    ".xls": "excel",
    ".pptx": "powerpoint",
    ".ppt": "powerpoint",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def discover_files(
    input_dir: Path,
    include_extensions: Optional[Set[str]] = None,
    exclude_extensions: Optional[Set[str]] = None,
    scope: Optional[str] = None
) -> List[Path]:
    """
    Recursively discover files in a directory with optional filtering.
    
    Scans directory tree applying extension and scope filters to build
    a list of files for processing.
    
    Args:
        input_dir (Path): Root directory to scan
        include_extensions (Optional[Set[str]]): Extensions to include (e.g., {'.pdf', '.csv'})
        exclude_extensions (Optional[Set[str]]): Extensions to exclude
        scope (Optional[str]): Scope subdirectory to focus on ('mba' or 'policy')
        
    Returns:
        List[Path]: List of discovered file paths matching criteria
        
    Raises:
        FileDiscoveryError: If directory doesn't exist or is inaccessible
        
    Side Effects:
        - Traverses filesystem
        - Logs discovery progress
        
    Example:
        files = discover_files(Path('./data'), include_extensions={'.csv'})
    """
    # Validate that the path exists and is a directory
    if not input_dir.exists():
        raise FileDiscoveryError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise FileDiscoveryError(f"Input path is not a directory: {input_dir}")

    # If scope is provided, adjust scanning directory
    if scope:
        scope_dir = input_dir / scope
        if scope_dir.exists() and scope_dir.is_dir():
            logger.info(f"Scanning scope-specific directory: {scope_dir}")
            scan_dir = scope_dir
        else:
            logger.warning(f"Scope directory {scope_dir} not found, scanning entire {input_dir}")
            scan_dir = input_dir
    else:
        scan_dir = input_dir

    discovered_files: List[Path] = []

    try:
        # Recursively walk the directory
        for file_path in scan_dir.rglob("*"):
            if not file_path.is_file():
                continue

            extension = file_path.suffix.lower()

            # Skip files with no extension
            if not extension:
                logger.debug(f"Skipping {file_path.name} - no extension")
                continue

            # Apply include filter if present
            if include_extensions:
                normalized_includes = {f".{ext.lstrip('.')}" for ext in include_extensions}
                if extension not in normalized_includes:
                    logger.debug(f"Skipping {file_path.name} - not in include list")
                    continue

            # Apply exclude filter if present
            if exclude_extensions:
                normalized_excludes = {f".{ext.lstrip('.')}" for ext in exclude_extensions}
                if extension in normalized_excludes:
                    logger.debug(f"Skipping {file_path.name} - in exclude list")
                    continue

            discovered_files.append(file_path)
            logger.debug(f"Discovered: {file_path.relative_to(input_dir)}")

    except Exception as exc:
        # Wrap errors in FileDiscoveryError with directory context
        raise FileDiscoveryError(f"Error scanning directory: {exc}", {"directory": str(scan_dir)})

    logger.info(f"Discovered {len(discovered_files)} files in {scan_dir}")
    return discovered_files


def detect_file_type(file_path: Path) -> str:
    """
    Detect file type category based on extension.
    
    Maps file extensions to logical categories for S3 organization.
    
    Args:
        file_path (Path): File path to analyze
        
    Returns:
        str: Category name ('pdf', 'csv', 'image', 'text', 'other')
        
    Mapping:
        - .pdf -> 'pdf'
        - .png, .jpg, .jpeg -> 'image'
        - .csv -> 'csv'
        - .txt, .log, .md -> 'text'
        - unknown -> 'other'
    """
    extension = file_path.suffix.lower()
    file_type = FILE_TYPE_MAPPING.get(extension, "other")
    logger.debug(f"File {file_path.name} detected as type: {file_type}")
    return file_type


def detect_scope_from_path(file_path: Path, input_dir: Path) -> Optional[str]:
    """
    Detect scope ('mba' or 'policy') from file path.
    
    Analyzes path components to determine data scope based on
    directory structure conventions.
    
    Args:
        file_path (Path): File path to analyze
        input_dir (Path): Base directory for relative path calculation
        
    Returns:
        Optional[str]: 'mba' or 'policy' if detected, None otherwise
        
    Detection Logic:
        1. Check relative path components for 'mba' or 'policy'
        2. Check parent directory names
        3. Return None if no scope indicator found
    """
    try:
        relative_path = file_path.relative_to(input_dir)
        parts = relative_path.parts
        if parts and parts[0].lower() in ("mba", "policy"):
            detected_scope = parts[0].lower()
            logger.debug(f"Detected scope '{detected_scope}' from path: {relative_path}")
            return detected_scope
    except ValueError:
        logger.debug(f"File {file_path} not relative to {input_dir}")

    # Try parent directories
    for parent in file_path.parents:
        parent_name = parent.name.lower()
        if parent_name in ("mba", "policy"):
            logger.debug(f"Detected scope '{parent_name}' from parent directory")
            return parent_name

    logger.debug(f"Could not detect scope for file: {file_path}")
    return None


def build_s3_key(scope: str, file_path: Path, prefix: str = "", auto_detect_type: bool = True) -> str:
    """
    Build structured S3 object key.
    
    Constructs S3 key with scope, type categorization, and filename.
    
    Args:
        scope (str): Data scope ('mba' or 'policy')
        file_path (Path): Source file path
        prefix (str): Optional prefix override (defaults to scope)
        auto_detect_type (bool): Whether to include type in path
        
    Returns:
        str: S3 key string (e.g., 'mba/csv/data.csv')
        
    Key Structure:
        - With type detection: {prefix}/{type}/{filename}
        - Without type detection: {prefix}/{filename}
    """
    base_prefix = prefix or f"{scope}/"
    if not base_prefix.endswith("/"):
        base_prefix += "/"

    if auto_detect_type:
        file_type = detect_file_type(file_path)
        s3_key = f"{base_prefix}{file_type}/{file_path.name}"
    else:
        s3_key = f"{base_prefix}{file_path.name}"

    logger.debug(f"Built S3 key: {s3_key}")
    return s3_key


def parse_extensions(extensions_str: str) -> Set[str]:
    """
    Parse comma-separated extensions into normalized set.
    
    Converts user input string to set of normalized extensions.
    
    Args:
        extensions_str (str): Comma-separated extensions (e.g., 'pdf,csv,docx')
        
    Returns:
        Set[str]: Normalized extensions with dots (e.g., {'.pdf', '.csv', '.docx'})
        
    Normalization:
        - Adds leading dot if missing
        - Converts to lowercase
        - Strips whitespace
    """
    if not extensions_str:
        return set()

    extensions: Set[str] = set()
    for ext in extensions_str.split(","):
        ext = ext.strip().lower()
        if ext:
            if not ext.startswith("."):
                ext = f".{ext}"
            extensions.add(ext)

    return extensions
