"""
AWS Lambda handler for S3 to RDS ETL with comprehensive error handling.

Processes S3 event notifications to load CSV files into MySQL RDS
with detailed logging and multi-status responses.

Module Input (Lambda Event):
    - S3 event records with bucket and key information
    - Lambda context with request ID and resource limits

Module Output (Lambda Response):
    dict containing:
        - statusCode: HTTP status (200 success, 207 partial, 500 error)
        - request_id: Lambda invocation ID
        - summary: Processing statistics
        - results: Per-file processing details
        - database_info: Connection metadata
"""

from __future__ import annotations
import json
import os
import traceback
from typing import Any, Dict
import boto3

from MBA.core.settings import settings
from MBA.core.logging_config import get_logger, setup_root_logger
from MBA.core.exceptions import MBAIngestionError
from MBA.etl.loader import CsvToMySQLLoader
from MBA.etl.db import health_check

# Configure root logger early for Lambda cold start
setup_root_logger()
logger = get_logger(__name__)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for S3 events with comprehensive error handling.
    
    Processes S3 PUT events to load CSV files into RDS MySQL with
    full audit trail and detailed error reporting.
    
    Args:
        event (Dict[str, Any]): S3 event containing:
            - Records: List of S3 event records
            - Each record contains s3.bucket.name and s3.object.key
            
        context (Any): Lambda context with:
            - aws_request_id: Unique invocation ID
            - memory_limit_in_mb: Allocated memory
            - get_remaining_time_in_millis(): Time before timeout
            
    Returns:
        Dict[str, Any]: Response containing:
            - statusCode (int): 200 (success), 207 (partial), 500 (error)
            - request_id (str): Lambda invocation ID for tracing
            - summary (dict): Aggregate statistics
            - results (List[dict]): Per-file processing details
            - database_info (dict): RDS connection information
            
    Side Effects:
        - Downloads CSV files from S3
        - Creates/updates MySQL tables
        - Loads data into RDS
        - Creates audit records
        - Logs all operations
            
    Error Handling:
        - Validates database connectivity before processing
        - Skips non-CSV files
        - Continues processing on individual file failures
        - Returns detailed error information per file
    """
    request_id = getattr(context, 'aws_request_id', 'unknown')
    logger.info("Lambda started - Request ID: %s", request_id)
    logger.debug("Full event: %s", json.dumps(event, indent=2))
    
    # Log Lambda context information
    try:
        if hasattr(context, 'memory_limit_in_mb'):
            memory_mb = int(context.memory_limit_in_mb) if context.memory_limit_in_mb else 0
            remaining_time = int(context.get_remaining_time_in_millis()) if hasattr(context, 'get_remaining_time_in_millis') else 0
            logger.info("Lambda context - Memory: %dMB, Remaining time: %dms", memory_mb, remaining_time)
    except (ValueError, AttributeError) as e:
        logger.debug("Could not log Lambda context: %s", e)
    
    # Validate environment
    try:
        logger.debug("Validating configuration...")
        db_health = health_check()
        logger.info("Database health check: %s", db_health)
        
        if db_health.get("status") != "healthy":
            logger.error("Database is not healthy: %s", db_health)
            return {
                "statusCode": 500,
                "error": "Database health check failed",
                "details": db_health,
                "request_id": request_id
            }
    except Exception as e:
        logger.error("Configuration validation failed: %s", e, exc_info=True)
        return {
            "statusCode": 500,
            "error": "Configuration validation failed",
            "details": str(e),
            "request_id": request_id
        }

    # Initialize S3 client
    try:
        s3_session = boto3.session.Session(region_name=settings.aws_default_region)
        s3 = s3_session.client("s3")
        logger.debug("S3 client initialized for region: %s", settings.aws_default_region)
    except Exception as e:
        logger.error("Failed to initialize S3 client: %s", e, exc_info=True)
        return {
            "statusCode": 500,
            "error": "Failed to initialize S3 client",
            "details": str(e),
            "request_id": request_id
        }

    # Process S3 records
    total_files = 0
    total_rows = 0
    results = []
    failed_files = 0

    records = event.get("Records", [])
    if not records:
        logger.warning("No S3 records found in event")
        return {
            "statusCode": 400,
            "error": "No S3 records found in event",
            "request_id": request_id
        }

    logger.info("Processing %d S3 records", len(records))

    for idx, rec in enumerate(records):
        try:
            # Extract S3 details
            s3_info = rec.get("s3", {})
            bucket_info = s3_info.get("bucket", {})
            object_info = s3_info.get("object", {})
            
            bucket = bucket_info.get("name")
            key = object_info.get("key")
            
            if not bucket or not key:
                logger.error("Record %d missing bucket or key: bucket=%s, key=%s", idx, bucket, key)
                results.append({
                    "record_index": idx,
                    "error": "Missing bucket or key in S3 record",
                    "bucket": bucket,
                    "key": key
                })
                failed_files += 1
                continue

            logger.info("Processing record %d: s3://%s/%s", idx, bucket, key)

            # Filter for target prefix
            if not key.lower().startswith("mba/csv/"):
                logger.info("Skipping non-target key: %s", key)
                results.append({
                    "record_index": idx,
                    "key": key,
                    "status": "skipped",
                    "reason": "Not in mba/csv/ prefix"
                })
                continue

            # Validate file extension
            if not key.lower().endswith('.csv'):
                logger.warning("Skipping non-CSV file: %s", key)
                results.append({
                    "record_index": idx,
                    "key": key,
                    "status": "skipped",
                    "reason": "Not a CSV file"
                })
                continue

            # Process the file
            try:
                logger.info("Starting ETL process for %s", key)
                loader = CsvToMySQLLoader(s3=s3, bucket=bucket, key=key)
                res = loader.run()
                
                total_files += 1
                total_rows += res.rows_inserted
                
                result_entry = {
                    "record_index": idx,
                    "key": key,
                    "bucket": bucket,
                    "table": res.table,
                    "rows_inserted": res.rows_inserted,
                    "delimiter": res.delimiter,
                    "audit_id": res.audit_id,
                    "status": "success"
                }
                results.append(result_entry)
                
                logger.info("Successfully processed %s: %d rows -> %s (audit: %s)", 
                           key, res.rows_inserted, res.table, res.audit_id)
                
            except Exception as exc:
                failed_files += 1
                error_msg = str(exc)
                error_type = type(exc).__name__
                
                logger.error("Failed to process %s (%s): %s", key, error_type, error_msg, exc_info=True)
                
                result_entry = {
                    "record_index": idx,
                    "key": key,
                    "bucket": bucket,
                    "status": "failed",
                    "error_type": error_type,
                    "error_message": error_msg,
                    "traceback": traceback.format_exc()[-1000:]  # Last 1000 chars
                }
                results.append(result_entry)

        except Exception as outer_exc:
            failed_files += 1
            logger.error("Unexpected error processing record %d: %s", idx, outer_exc, exc_info=True)
            results.append({
                "record_index": idx,
                "status": "failed",
                "error_type": type(outer_exc).__name__,
                "error_message": str(outer_exc),
                "traceback": traceback.format_exc()[-1000:]
            })

    # Prepare final response
    success_rate = (total_files / len(records)) * 100 if records else 0
    
    response = {
        "statusCode": 200 if failed_files == 0 else 207,  # 207 Multi-Status for partial success
        "request_id": request_id,
        "summary": {
            "total_records": len(records),
            "files_processed": total_files,
            "files_failed": failed_files,
            "files_skipped": len(records) - total_files - failed_files,
            "total_rows_inserted": total_rows,
            "success_rate_percent": round(success_rate, 2)
        },
        "results": results,
        "database_info": {
            "host": settings.RDS_HOST,
            "database": settings.RDS_DATABASE,
            "region": settings.aws_default_region
        }
    }

    # Log final summary
    if failed_files == 0:
        logger.info("Lambda completed successfully - %d files, %d rows inserted", 
                   total_files, total_rows)
    else:
        logger.warning("Lambda completed with errors - %d success, %d failed, %d total rows", 
                      total_files, failed_files, total_rows)

    return response