"""
db.py
RDS/MySQL engine factory + small helpers using SQLAlchemy.
Improved version with better error handling and logging.
"""

from __future__ import annotations
from contextlib import contextmanager
from typing import Generator, Iterable, Mapping, Any
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import OperationalError, DatabaseError

from MBA.core.settings import settings
from MBA.core.logging_config import get_logger

logger = get_logger(__name__)
_engine: Engine | None = None

def _server_url_and_db(url: str) -> tuple[str, str]:
    """Split database URL into server URL and database name."""
    if "/" not in url.rsplit("/", 1)[-1]:
        return url, ""
    base, db = url.rsplit("/", 1)
    return base, db

def _test_mysql_connection(url: str) -> bool:
    """Test if we can connect to MySQL server (without database)."""
    try:
        server_url, _ = _server_url_and_db(url)
        test_engine = create_engine(server_url, pool_pre_ping=True)
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            logger.info("MySQL server connection test successful: %s", result)
        test_engine.dispose()
        return True
    except Exception as e:
        logger.error("MySQL server connection test failed: %s", e)
        return False

def _create_database_if_not_exists(url: str, dbname: str) -> bool:
    """Create database if it doesn't exist. Returns True if created or already exists."""
    try:
        server_url, _ = _server_url_and_db(url)
        logger.info("Attempting to create database '%s' if it doesn't exist", dbname)
        
        # Connect to MySQL server (not specific database)
        server_engine = create_engine(server_url, pool_pre_ping=True)
        
        with server_engine.connect() as conn:
            # Check if database exists
            check_sql = text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :dbname")
            result = conn.execute(check_sql, {"dbname": dbname}).fetchone()
            
            if result:
                logger.info("Database '%s' already exists", dbname)
                server_engine.dispose()
                return True
            
            # Create database
            create_sql = text(f"CREATE DATABASE `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.execute(create_sql)
            conn.commit()
            logger.info("Successfully created database '%s'", dbname)
            
        server_engine.dispose()
        return True
        
    except Exception as e:
        logger.error("Failed to create database '%s': %s", dbname, e, exc_info=True)
        return False

def get_engine() -> Engine:
    """
    Return SQLAlchemy Engine with improved error handling and logging.
    Automatically creates database if it doesn't exist.
    """
    global _engine
    if _engine is not None:
        return _engine
    
    url = settings.db_url()
    logger.info("Initializing SQLAlchemy engine for MySQL")
    logger.debug("Database URL (password masked): %s", url.replace(settings.RDS_PASSWORD, "***"))
    
    # Test basic MySQL connectivity first
    if not _test_mysql_connection(url):
        raise DatabaseError("Cannot connect to MySQL server", None, None)
    
    try:
        # Try connecting to the specific database
        logger.info("Attempting to connect to database...")
        eng = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        
        with eng.connect() as conn:
            # Test the connection
            result = conn.execute(text("SELECT DATABASE()")).scalar()
            logger.info("Successfully connected to database: %s", result)
        
        _engine = eng
        return _engine
        
    except OperationalError as e:
        error_code = getattr(e.orig, "args", [None])[0] if hasattr(e, 'orig') else None
        
        if error_code == 1049:  # Unknown database
            server_url, dbname = _server_url_and_db(url)
            if not dbname:
                logger.error("No database name found in URL")
                raise
            
            logger.warning("Database '%s' not found (error 1049). Attempting to create...", dbname)
            
            # Create the database
            if not _create_database_if_not_exists(url, dbname):
                raise DatabaseError(f"Failed to create database '{dbname}'", None, None)
            
            # Retry connection to the newly created database
            logger.info("Retrying connection to newly created database...")
            eng = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
            
            with eng.connect() as conn:
                result = conn.execute(text("SELECT DATABASE()")).scalar()
                logger.info("Successfully connected to created database: %s", result)
            
            _engine = eng
            return _engine
        else:
            logger.error("Database connection failed with error code %s: %s", error_code, e)
            raise
    
    except Exception as e:
        logger.error("Unexpected database connection error: %s", e, exc_info=True)
        raise

@contextmanager
def connect() -> Generator[Connection, None, None]:
    """Context manager for database connections with retry logic."""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            eng = get_engine()
            conn = eng.connect()
            logger.debug("Database connection established (attempt %d)", attempt + 1)
            try:
                yield conn
                return
            finally:
                conn.close()
                logger.debug("Database connection closed")
        except Exception as e:
            logger.warning("Connection attempt %d failed: %s", attempt + 1, e)
            if attempt == max_retries - 1:
                logger.error("All connection attempts failed")
                raise
            time.sleep(retry_delay)

def exec_sql(sql: str, params: Mapping[str, Any] | None = None) -> None:
    """Execute SQL with improved error handling."""
    logger.debug("Executing SQL: %s", sql[:100] + "..." if len(sql) > 100 else sql)
    start_time = time.time()
    
    try:
        with connect() as conn:
            conn.execute(text(sql), params or {})
            conn.commit()
        
        duration = (time.time() - start_time) * 1000
        logger.debug("SQL executed successfully in %.2fms", duration)
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("SQL execution failed after %.2fms: %s", duration, e, exc_info=True)
        raise

def bulk_insert(table: str, rows: Iterable[Mapping[str, Any]]) -> int:
    """Bulk insert with improved logging and error handling."""
    rows = list(rows)
    if not rows:
        logger.debug("No rows to insert into table '%s'", table)
        return 0
    
    row_count = len(rows)
    logger.debug("Bulk inserting %d rows into table '%s'", row_count, table)
    start_time = time.time()
    
    try:
        cols = list(rows[0].keys())
        placeholders = ", ".join([f":{c}" for c in cols])
        sql = f"INSERT INTO `{table}` ({', '.join(f'`{c}`' for c in cols)}) VALUES ({placeholders})"
        
        with connect() as conn:
            conn.execute(text(sql), rows)
            conn.commit()
        
        duration = (time.time() - start_time) * 1000
        logger.info("Successfully inserted %d rows into '%s' in %.2fms", row_count, table, duration)
        return row_count
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("Bulk insert failed after %.2fms: %s", duration, e, exc_info=True)
        raise

def health_check() -> dict:
    """Database health check for monitoring."""
    try:
        start_time = time.time()
        with connect() as conn:
            result = conn.execute(text("SELECT 1 as health_check")).scalar()
            duration = (time.time() - start_time) * 1000
            
        return {
            "status": "healthy",
            "response_time_ms": round(duration, 2),
            "database": settings.RDS_DATABASE,
            "host": settings.RDS_HOST
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": settings.RDS_DATABASE,
            "host": settings.RDS_HOST
        }