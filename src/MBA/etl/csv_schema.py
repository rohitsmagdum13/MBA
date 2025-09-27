"""
csv_schema.py
Infer MySQL table schema from a CSV file:
- Reads header to get column names.
- Samples rows to infer types and max lengths.
- Produces CREATE TABLE DDL with sane defaults.

Notes:
- Exact table name = sanitized base filename (without extension).
- Column names are normalized to snake_case and backticked in SQL.
- Type mapping is conservative to avoid load-time failures.
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
    Infer column stats from CSV bytes.
    Returns: (dialect_delimiter, stats)
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
    Choose the narrowest MySQL type compatible with observations.
    Precedence: datetime > date > int > float > bool > varchar/longtext
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
    Generate CREATE TABLE IF NOT EXISTS DDL with backticked identifiers.
    """
    lines = []
    for c in cols:
        col_type = mysql_type_for(c)
        null_sql = "NULL" if c.nullable else "NOT NULL"
        lines.append(f"  `{c.snake}` {col_type} {null_sql}")
    cols_sql = ",\n".join(lines)
    return f"CREATE TABLE IF NOT EXISTS `{table}` (\n{cols_sql}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
