import sqlite3
from pathlib import Path

# Get database path
app_data_dir = Path.home() / "AppData" / "Local" / "PowerBI Migration Toolkit"
db_path = app_data_dir / "data" / "fabric_migration.db"

print(f"Database: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get DimDate_x (object_id=2) columns and check if they make sense
print("="*80)
print("DIMDATE_X (object_id=2) - First 20 columns:")
print("="*80)

cursor.execute("""
    SELECT column_name, source_column, data_type
    FROM columns
    WHERE object_id = 2
    ORDER BY column_id
    LIMIT 20
""")

for col_name, source, dtype in cursor.fetchall():
    print(f"  {col_name:40} <- {source:30} ({dtype})")

# Check if there are ANY actual date-related columns
cursor.execute("""
    SELECT column_name
    FROM columns
    WHERE object_id = 2 
    AND (column_name LIKE '%Date%' OR column_name LIKE '%Year%' OR column_name LIKE '%Month%' OR column_name LIKE '%Quarter%')
""")

date_cols = cursor.fetchall()
print(f"\n✓ Found {len(date_cols)} date-related columns in DimDate_x:")
for col in date_cols[:10]:
    print(f"  - {col[0]}")

# Now let's check a product-related column and see which tables it appears in
print(f"\n{'='*80}")
print("CHECKING 'ProductKey' COLUMN ACROSS ALL TABLES")
print("="*80)

cursor.execute("""
    SELECT 
        o.object_id,
        o.object_name,
        c.column_name,
        c.source_column
    FROM columns c
    JOIN data_objects o ON c.object_id = o.object_id
    WHERE c.column_name LIKE '%ProductKey%' OR c.source_column LIKE '%ProductKey%'
    ORDER BY o.object_name
""")

product_key_refs = cursor.fetchall()
for obj_id, obj_name, col_name, source in product_key_refs:
    print(f"  object_id={obj_id} | {obj_name:30} | {col_name:40} <- {source}")

conn.close()

print(f"\n{'='*80}")
print("ANALYSIS")
print("="*80)
print("If ProductKey appears in DimDate_x, there's a bug in column assignment!")
print("ProductKey should ONLY be in DimProduct_x and FactSales_x")
