"""
Check MySQL schema for available columns.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from MBA.etl.db import connect
from sqlalchemy import text

def check_memberdata_schema():
    """Check memberdata table schema."""
    try:
        with connect() as conn:
            # Get table structure
            result = conn.execute(text("DESCRIBE memberdata")).fetchall()
            
            print("memberdata table columns:")
            for row in result:
                print(f"  {row[0]} - {row[1]}")
            
            # Check if plan_name exists
            columns = [row[0] for row in result]
            print(f"\nplan_name exists: {'plan_name' in columns}")
            print(f"group_number exists: {'group_number' in columns}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_memberdata_schema()