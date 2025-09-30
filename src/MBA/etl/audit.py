"""
Lightweight audit trail for CSV to MySQL loads with improved error handling.

Tracks ETL operations from S3 to MySQL with timing, row counts, and error details.

Module Input:
    - S3 object metadata (bucket, key, size, hash)
    - ETL operation results (success/failure, row counts)
    - Lambda context (request ID if available)

Module Output:
    - Audit records in MySQL ingestion_audit table
    - Audit IDs for tracking operations
    - Status reports for monitoring
"""

from __future__ import annotations
import uuid
import time
from sqlalchemy import text
from MBA.etl.db import exec_sql, connect
from MBA.core.logging_config import get_logger

logger = get_logger(__name__)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `ingestion_audit` (
  `id`            VARCHAR(36)  NOT NULL,
  `s3_bucket`     VARCHAR(255) NOT NULL,
  `s3_key`        TEXT         NOT NULL,
  `table_name`    VARCHAR(255) NOT NULL,
  `content_md5`   CHAR(32)     NOT NULL,
  `bytes`         BIGINT       NOT NULL,
  `started_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at`   DATETIME     NULL,
  `duration_ms`   INT          NULL,
  `rows_inserted` INT          NULL,
  `status`        ENUM('STARTED','SUCCESS','FAILED') NOT NULL,
  `error_message` TEXT         NULL,
  `lambda_request_id` VARCHAR(64) NULL,
  `retry_count`   INT          DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_started_at` (`started_at`),
  INDEX `idx_s3_key` (`s3_key`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

class AuditLogger:
    """
    Provides static methods for ETL audit trail management.
    
    Manages audit records for tracking CSV ingestion from S3 to MySQL,
    including timing, success metrics, and error details.
    """
    @staticmethod
    def ensure_table() -> None:
        """
        Create audit table if it doesn't exist.
        
        Creates the ingestion_audit table with appropriate schema for
        tracking ETL operations including timing, status, and errors.
        
        Input:
            None
            
        Output:
            None
            
        Side Effects:
            - Creates ingestion_audit table in MySQL
            - Logs operation timing
            
        Raises:
            Exception: If table creation fails
        """
        try:
            logger.debug("Ensuring ingestion_audit table exists")
            start_time = time.time()
            exec_sql(_CREATE_SQL)
            duration = (time.time() - start_time) * 1000
            logger.debug("Audit table ensured in %.2fms", duration)
        except Exception as e:
            logger.error("Failed to create audit table: %s", e, exc_info=True)
            raise

    @staticmethod
    def start(s3_bucket: str, s3_key: str, table_name: str, content_md5: str, 
              size_bytes: int, lambda_request_id: str = None) -> str:
        """
        Start audit trail for an ETL operation.
        
        Creates initial audit record marking the start of CSV processing.
        
        Args:
            s3_bucket (str): Source S3 bucket name
            s3_key (str): Source S3 object key
            table_name (str): Target MySQL table name
            content_md5 (str): MD5 hash of content (32 chars)
            size_bytes (int): File size in bytes
            lambda_request_id (Optional[str]): Lambda invocation ID
            
        Returns:
            str: UUID audit ID for tracking this operation
            
        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If database insertion fails
            
        Side Effects:
            - Inserts record into ingestion_audit table
            - Ensures audit table exists
        """
        
        # Validate inputs
        if not all([s3_bucket, s3_key, table_name, content_md5]):
            raise ValueError("All audit parameters (bucket, key, table, md5) are required")
        
        if size_bytes < 0:
            raise ValueError("Size bytes cannot be negative")
        
        try:
            AuditLogger.ensure_table()
            audit_id = str(uuid.uuid4())
            
            logger.info("Starting audit trail - ID: %s, Key: %s, Table: %s, Size: %d bytes", 
                       audit_id, s3_key, table_name, size_bytes)
            
            sql = """
            INSERT INTO ingestion_audit
                (id, s3_bucket, s3_key, table_name, content_md5, bytes, status, lambda_request_id)
            VALUES
                (:id, :bucket, :key, :table, :md5, :size, 'STARTED', :request_id)
            """
            
            params = {
                "id": audit_id,
                "bucket": s3_bucket[:255],  # Truncate if too long
                "key": s3_key,
                "table": table_name[:255],  # Truncate if too long
                "md5": content_md5,
                "size": size_bytes,
                "request_id": lambda_request_id[:64] if lambda_request_id else None
            }
            
            start_time = time.time()
            with connect() as conn:
                conn.execute(text(sql), params)
                conn.commit()
            
            duration = (time.time() - start_time) * 1000
            logger.info("Audit STARTED - ID: %s, Duration: %.2fms", audit_id, duration)
            return audit_id
            
        except Exception as e:
            logger.error("Failed to start audit trail for %s: %s", s3_key, e, exc_info=True)
            raise

    @staticmethod
    def success(audit_id: str, rows_inserted: int, duration_ms: int) -> None:
        """
        Mark audit record as successful.
        
        Updates audit record with success status and metrics.
        
        Args:
            audit_id (str): UUID from start() call
            rows_inserted (int): Number of rows loaded to MySQL
            duration_ms (int): Total operation time in milliseconds
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If database update fails
            
        Side Effects:
            - Updates audit record status to SUCCESS
            - Records completion time and metrics
        """
        
        if not audit_id:
            raise ValueError("Audit ID is required")
        
        if rows_inserted < 0:
            raise ValueError("Rows inserted cannot be negative")
        
        if duration_ms < 0:
            raise ValueError("Duration cannot be negative")
        
        try:
            logger.debug("Marking audit as successful - ID: %s, Rows: %d", audit_id, rows_inserted)
            
            sql = """
            UPDATE ingestion_audit
               SET finished_at = CURRENT_TIMESTAMP,
                   duration_ms = :duration,
                   rows_inserted = :rows,
                   status = 'SUCCESS',
                   error_message = NULL
             WHERE id = :id
            """
            
            params = {
                "id": audit_id,
                "duration": duration_ms,
                "rows": rows_inserted
            }
            
            start_time = time.time()
            with connect() as conn:
                result = conn.execute(text(sql), params)
                if result.rowcount == 0:
                    logger.warning("No audit record found with ID: %s", audit_id)
                conn.commit()
            
            update_duration = (time.time() - start_time) * 1000
            logger.info("Audit SUCCESS - ID: %s, Rows: %d, ETL Duration: %dms, Update Duration: %.2fms", 
                       audit_id, rows_inserted, duration_ms, update_duration)
            
        except Exception as e:
            logger.error("Failed to mark audit as successful for ID %s: %s", audit_id, e, exc_info=True)
            raise

    @staticmethod
    def failure(audit_id: str, error_message: str, retry_count: int = 0) -> None:
        """
        Mark audit record as failed.
        
        Updates audit record with failure status and error details.
        
        Args:
            audit_id (str): UUID from start() call
            error_message (str): Error description (truncated to 4000 chars)
            retry_count (int): Number of retry attempts made
            
        Side Effects:
            - Updates audit record status to FAILED
            - Records error message and retry count
            - Does not raise exceptions (logs errors internally)
        """
        
        if not audit_id:
            raise ValueError("Audit ID is required")
        
        if not error_message:
            error_message = "Unknown error"
        
        try:
            # Truncate error message if too long for database field
            truncated_error = error_message[:4000] if len(error_message) > 4000 else error_message
            
            logger.warning("Marking audit as failed - ID: %s, Error: %s", audit_id, truncated_error[:200])
            
            sql = """
            UPDATE ingestion_audit
               SET finished_at = CURRENT_TIMESTAMP,
                   status = 'FAILED',
                   error_message = :error,
                   retry_count = :retry_count
             WHERE id = :id
            """
            
            params = {
                "id": audit_id,
                "error": truncated_error,
                "retry_count": retry_count
            }
            
            start_time = time.time()
            with connect() as conn:
                result = conn.execute(text(sql), params)
                if result.rowcount == 0:
                    logger.warning("No audit record found with ID: %s", audit_id)
                conn.commit()
            
            update_duration = (time.time() - start_time) * 1000
            logger.warning("Audit FAILED - ID: %s, Retry Count: %d, Update Duration: %.2fms", 
                          audit_id, retry_count, update_duration)
            
        except Exception as e:
            logger.error("Failed to mark audit as failed for ID %s: %s", audit_id, e, exc_info=True)
            # Don't re-raise here to avoid masking the original error

    @staticmethod
    def get_audit_status(audit_id: str) -> dict:
        """Get current status of an audit record."""
        try:
            sql = """
            SELECT id, s3_bucket, s3_key, table_name, status, started_at, finished_at,
                   duration_ms, rows_inserted, error_message, retry_count
            FROM ingestion_audit
            WHERE id = :id
            """
            
            with connect() as conn:
                result = conn.execute(text(sql), {"id": audit_id}).fetchone()
                
            if not result:
                return {"status": "not_found", "audit_id": audit_id}
            
            return {
                "audit_id": result.id,
                "s3_bucket": result.s3_bucket,
                "s3_key": result.s3_key,
                "table_name": result.table_name,
                "status": result.status,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "finished_at": result.finished_at.isoformat() if result.finished_at else None,
                "duration_ms": result.duration_ms,
                "rows_inserted": result.rows_inserted,
                "error_message": result.error_message,
                "retry_count": result.retry_count
            }
            
        except Exception as e:
            logger.error("Failed to get audit status for ID %s: %s", audit_id, e, exc_info=True)
            return {"status": "error", "audit_id": audit_id, "error": str(e)}

    @staticmethod
    def get_recent_audits(limit: int = 10) -> list:
        """Get recent audit records for monitoring."""
        try:
            sql = """
            SELECT id, s3_key, table_name, status, started_at, finished_at,
                   duration_ms, rows_inserted, error_message
            FROM ingestion_audit
            ORDER BY started_at DESC
            LIMIT :limit
            """
            
            with connect() as conn:
                results = conn.execute(text(sql), {"limit": limit}).fetchall()
            
            return [
                {
                    "audit_id": row.id,
                    "s3_key": row.s3_key,
                    "table_name": row.table_name,
                    "status": row.status,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                    "duration_ms": row.duration_ms,
                    "rows_inserted": row.rows_inserted,
                    "error_message": row.error_message[:100] + "..." if row.error_message and len(row.error_message) > 100 else row.error_message
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error("Failed to get recent audits: %s", e, exc_info=True)
            return []