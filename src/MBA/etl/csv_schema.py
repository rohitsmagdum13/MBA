"""
Infer MySQL table schema from CSV files.

Analyzes CSV structure and data to generate appropriate MySQL CREATE TABLE
statements with proper data types and constraints.

Module Input:
    - CSV file content as bytes
    - Number of rows to sample for type inference

Module Output:
    - Column statistics with inferred types
    - CREATE TABLE DDL statements
    - Delimiter detection results
"""

from __future__ import annotations
import csv
import io
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from MBA.core.logging_config import get_logger

logger = get_logger(__name__)

_SNAKE = re.compile(r"[^0-9a-zA-Z]+")

def to_snake(name: str) -> str:
    """
    Convert arbitrary string to snake_case identifier.
    
    Normalizes column names for MySQL compatibility by converting to
    snake_case and handling special characters.
    
    Args:
        name (str): Original column name from CSV
        
    Returns:
        str: MySQL-safe snake_case identifier
        
    Examples:
        "First Name" -> "first_name"
        "ZIP-Code" -> "zip_code"
        "123Data" -> "c_123data"
    """
    base = _SNAKE.sub("_", name).strip("_")
    # avoid starting with digit
    if base and base[0].isdigit():
        base = f"c_{base}"
    return base.lower() or "col"

@dataclass
class ColumnStat:
    name: str
    snake: str
    is_int: bool = True
    is_float: bool = True
    is_bool: bool = True
    is_date: bool = True
    is_datetime: bool = True
    max_len: int = 0
    nullable: bool = False

def _maybe_bool(v: str) -> bool:
    return v.lower() in {"true","false","t","f","yes","no","y","n","0","1"}

def _maybe_int(v: str) -> bool:
    try:
        int(v)
        return True
    except Exception:
        return False

def _maybe_float(v: str) -> bool:
    try:
        float(v)
        return True
    except Exception:
        return False

def _maybe_date(v: str) -> bool:
    # try a few common formats
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y"):
        try:
            datetime.strptime(v, fmt)
            return True
        except Exception:
            continue
    return False

def _maybe_datetime(v: str) -> bool:
    for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S","%d-%m-%Y %H:%M:%S"):
        try:
            datetime.strptime(v, fmt)
            return True
        except Exception:
            continue
    return False

def infer_schema_from_csv_bytes(content: bytes, sample_rows: int = 500) -> Tuple[str, List[ColumnStat]]:
    """
    Infer column statistics from CSV bytes.
    
    Analyzes CSV content to detect delimiter, column types, and constraints
    by sampling rows and testing type compatibility.
    
    Args:
        content (bytes): Raw CSV file content
        sample_rows (int): Maximum rows to analyze for type inference
        
    Returns:
        Tuple[str, List[ColumnStat]]: Tuple containing:
            - str: Detected delimiter character
            - List[ColumnStat]: Column statistics for each field
            
    Raises:
        ValueError: If CSV has no header row
        
    Side Effects:
        - None (pure function)
    """
    # Use csv.Sniffer to detect delimiter
    head = content[:8192].decode("utf-8", errors="ignore")
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(head)
        delim = dialect.delimiter
    except Exception:
        delim = ","
    f = io.StringIO(content.decode("utf-8", errors="ignore"))
    rdr = csv.reader(f, delimiter=delim)
    header = next(rdr, [])
    if not header:
        raise ValueError("CSV has no header row")

    stats = [ColumnStat(name=h.strip(), snake=to_snake(h)) for h in header]

    for idx, row in enumerate(rdr, 1):
        if not row:
            continue
        for i, raw in enumerate(row[:len(stats)]):
            v = (raw or "").strip()
            if v == "":
                stats[i].nullable = True
                continue
            # track max length for VARCHAR
            stats[i].max_len = max(stats[i].max_len, len(v))
            # try types
            if not _maybe_int(v): stats[i].is_int = False
            if not _maybe_float(v): stats[i].is_float = False
            if not _maybe_bool(v): stats[i].is_bool = False
            if not _maybe_date(v): stats[i].is_date = False
            if not _maybe_datetime(v): stats[i].is_datetime = False
        if idx >= sample_rows:
            break

    return delim, stats

def mysql_type_for(col: ColumnStat) -> str:
    """
    Choose appropriate MySQL data type for column.
    
    Selects the most specific MySQL type that can accommodate all
    observed values in the column.
    
    Args:
        col (ColumnStat): Column statistics from inference
        
    Returns:
        str: MySQL type definition (e.g., "VARCHAR(255)", "BIGINT")
        
    Type Precedence:
        DATETIME > DATE > BIGINT > DECIMAL > TINYINT > VARCHAR > TEXT
    """
    # datetime vs date
    if col.is_datetime: return "DATETIME"
    if col.is_date:     return "DATE"
    # numeric
    if col.is_int and not col.nullable:
        # fits in BIGINT safely
        return "BIGINT"
    if col.is_float and not col.nullable:
        # decimal(38,10) for safety (tune as needed)
        return "DECIMAL(38,10)"
    # boolean-like? store as TINYINT(1)
    if col.is_bool and not col.is_int:
        return "TINYINT(1)"
    # strings: choose VARCHAR up to 1024, otherwise TEXT
    width = max(1, min(col.max_len or 255, 1024))
    return f"VARCHAR({width})" if width <= 1024 else "TEXT"

def build_create_table_sql(table: str, cols: List[ColumnStat]) -> str:
    """
    Generate CREATE TABLE IF NOT EXISTS DDL.
    
    Builds complete MySQL table definition with proper escaping and
    character set configuration.
    
    Args:
        table (str): Target table name
        cols (List[ColumnStat]): Column definitions from inference
        
    Returns:
        str: Complete CREATE TABLE statement
        
    Example Output:
        CREATE TABLE IF NOT EXISTS `member_data` (
          `member_id` BIGINT NOT NULL,
          `first_name` VARCHAR(100) NULL,
          `enrollment_date` DATE NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    lines = []
    for c in cols:
        col_type = mysql_type_for(c)
        null_sql = "NULL" if c.nullable else "NOT NULL"
        lines.append(f"  `{c.snake}` {col_type} {null_sql}")
    cols_sql = ",\n".join(lines)
    return f"CREATE TABLE IF NOT EXISTS `{table}` (\n{cols_sql}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
