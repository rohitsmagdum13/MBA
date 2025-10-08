"""
Analyze CSV files and create proper database schema.
"""

import pandas as pd
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from MBA.etl.csv_schema import infer_schema_from_csv_bytes, build_create_table_sql

def analyze_csv_files():
    """Analyze all CSV files and show their schemas."""
    
    csv_dir = Path("data/mba/csv")
    csv_files = list(csv_dir.glob("*.csv"))
    
    print("=== CSV SCHEMA ANALYSIS ===\n")
    
    for csv_file in csv_files:
        print(f"📄 {csv_file.name}")
        print("-" * 50)
        
        try:
            # Read CSV to show columns
            df = pd.read_csv(csv_file)
            print(f"Columns ({len(df.columns)}): {list(df.columns)}")
            print(f"Rows: {len(df)}")
            
            # Infer schema using MBA's schema inference
            with open(csv_file, 'rb') as f:
                content = f.read()
            
            delimiter, stats = infer_schema_from_csv_bytes(content)
            
            print(f"Delimiter: '{delimiter}'")
            print("Schema:")
            for stat in stats:
                print(f"  {stat.name} -> {stat.snake} (nullable: {stat.nullable})")
            
            # Generate CREATE TABLE
            table_name = csv_file.stem.lower()
            ddl = build_create_table_sql(table_name, stats)
            print(f"\nCREATE TABLE SQL:")
            print(ddl)
            
        except Exception as e:
            print(f"Error analyzing {csv_file.name}: {e}")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    analyze_csv_files()