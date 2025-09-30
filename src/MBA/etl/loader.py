"""
CSV to MySQL ETL loader with schema inference and auditing.

Orchestrates the complete ETL pipeline from S3 download through
schema creation to data loading with comprehensive audit trail.

Module Input:
    - S3 object coordinates (bucket, key)
    - Batch size configuration
    - AWS S3 client

Module Output:
    - Loaded data in MySQL tables
    - Audit records
    - Load statistics
"""

from __future__ import annotations
import csv
import io
import os
import time
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, List
import boto3

from MBA.core.logging_config import get_logger
from MBA.etl.db import exec_sql, bulk_insert
from MBA.etl.csv_schema import infer_schema_from_csv_bytes, build_create_table_sql, to_snake
from MBA.etl.transforms import transform_row
from MBA.etl.audit import AuditLogger

logger = get_logger(__name__)

@dataclass
class LoadResult:
    table: str
    delimiter: str
    rows_inserted: int
    audit_id: str | None = None

class CsvToMySQLLoader:
    """
    End-to-end ETL for a single CSV S3 object into MySQL.
    
    Manages the complete pipeline including download, schema inference,
    table creation, data transformation, and bulk loading with audit.
    
    Attributes:
        s3 (boto3.client): S3 client for object operations
        bucket (str): Source S3 bucket
        key (str): Source S3 object key
    """

    def __init__(self, s3: boto3.client, bucket: str, key: str):
        """
        Initialize loader with S3 coordinates.
        
        Args:
            s3 (boto3.client): Configured S3 client
            bucket (str): S3 bucket name
            key (str): S3 object key
        """
        self.s3 = s3
        self.bucket = bucket
        self.key = key

    def _download(self) -> bytes:
        """Download S3 object into memory (bytes)."""
        logger.info("Downloading s3://%s/%s", self.bucket, self.key)
        obj = self.s3.get_object(Bucket=self.bucket, Key=self.key)
        return obj["Body"].read()

    def _table_name(self) -> str:
        """Derive table name from file name (no extension), snake_cased."""
        base = os.path.basename(self.key)
        name = base.rsplit(".", 1)[0]
        return to_snake(name)

    @staticmethod
    def _md5(b: bytes) -> str:
        """Hex MD5 of content (for audit & idempotency checks if desired)."""
        h = hashlib.md5()  # nosec: audit only, not for security
        h.update(b)
        return h.hexdigest()

    def run(self, batch_size: int = 2000) -> LoadResult:
        """
        Execute complete ETL pipeline with auditing.
        
        Downloads CSV from S3, infers schema, creates table, transforms
        data, and loads into MySQL with full audit trail.
        
        Args:
            batch_size (int): Number of rows per insert batch
            
        Returns:
            LoadResult: Dataclass containing:
                - table (str): Created table name
                - delimiter (str): Detected CSV delimiter
                - rows_inserted (int): Total rows loaded
                - audit_id (Optional[str]): Audit trail UUID
                
        Raises:
            Exception: On ETL failure (after audit record)
            
        Side Effects:
            - Downloads S3 object
            - Creates/updates MySQL table
            - Inserts data rows
            - Creates audit records
        """
        t0 = time.time()

        # 1) Fetch file
        raw = self._download()
        size = len(raw)
        md5 = self._md5(raw)
        table = self._table_name()

        # 2) Audit STARTED
        audit_id = AuditLogger.start(
            s3_bucket=self.bucket,
            s3_key=self.key,
            table_name=table,
            content_md5=md5,
            size_bytes=size,
        )

        try:
            # 3) Infer schema + CREATE TABLE (idempotent)
            delim, stats = infer_schema_from_csv_bytes(raw)
            ddl = build_create_table_sql(table, stats)
            exec_sql(ddl)

            # 4) Stream rows → transform → bulk insert
            rows_inserted = 0
            f = io.StringIO(raw.decode("utf-8", errors="ignore"))
            rdr = csv.DictReader(f, delimiter=delim)
            batch: List[Dict[str, Any]] = []

            # header rename (original -> snake)
            rename = {h: s.snake for h, s in zip(rdr.fieldnames or [], stats)}

            for row in rdr:
                normalized = {rename[k]: (row.get(k, "") or "").strip() for k in rename.keys()}
                normalized = transform_row(normalized)
                batch.append(normalized)
                if len(batch) >= batch_size:
                    rows_inserted += bulk_insert(table, batch)
                    batch.clear()

            if batch:
                rows_inserted += bulk_insert(table, batch)

            # 5) Audit SUCCESS
            duration_ms = int((time.time() - t0) * 1000)
            AuditLogger.success(audit_id, rows_inserted, duration_ms)
            logger.info("Loaded %d rows into `%s` (audit_id=%s)", rows_inserted, table, audit_id)

            return LoadResult(table=table, delimiter=delim, rows_inserted=rows_inserted, audit_id=audit_id)

        except Exception as exc:
            # 6) Audit FAILED
            duration_ms = int((time.time() - t0) * 1000)
            AuditLogger.failure(audit_id, f"{type(exc).__name__}: {exc}")
            logger.error("ETL failed for %s: %s", self.key, exc, exc_info=True)
            raise
