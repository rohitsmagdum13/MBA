"""
transforms.py
Row-level transform hooks applied post-parse, pre-load.
Add your custom business rules here.
"""

from __future__ import annotations
from typing import Dict, Any

def transform_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example no-op transform (normalize empties).
    """
    return {k: (None if (v == "" or v is None) else v) for k, v in row.items()}
