#!/usr/bin/env python3
"""Quick test to validate CSV files."""
import pandas as pd
from pathlib import Path

test_files = [
    Path("test_data/maxNetPos_20241119.csv"),
    Path("test_data/maxNetPos_20241120.csv"),
]

for file_path in test_files:
    if not file_path.exists():
        print(f"❌ {file_path} does not exist")
        continue

    print(f"\n{'='*60}")
    print(f"Testing: {file_path}")
    print(f"{'='*60}")

    # Check file size
    size = file_path.stat().st_size
    print(f"File size: {size} bytes")

    # Try reading with different delimiters and encodings
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1']
    delimiters = [',', ';']

    success = False
    for encoding in encodings:
        for delimiter in delimiters:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=delimiter,
                    encoding_errors='ignore'
                )
                if len(df.columns) > 1:
                    print(f"✅ Success with encoding={encoding}, delimiter='{delimiter}'")
                    print(f"   Columns: {len(df.columns)}")
                    print(f"   Rows: {len(df)}")
                    print(f"   First few columns: {list(df.columns[:5])}")
                    success = True
                    break
            except Exception as e:
                continue
        if success:
            break

    if not success:
        print(f"❌ Failed to read CSV")
        # Show first 200 bytes
        with open(file_path, 'rb') as f:
            print(f"First 200 bytes: {f.read(200)}")

print(f"\n{'='*60}")
print("Test complete!")
