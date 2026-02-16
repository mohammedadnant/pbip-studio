"""
Comprehensive Database Relationships and Constraints Checker
Checks all tables, foreign keys, and relationships for issues.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple
import os

def get_database_path():
    """Get database path from AppData."""
    appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~/.local/share'))
    db_dir = Path(appdata) / 'PowerBI Migration Toolkit' / 'data'
    return str(db_dir / 'fabric_migration.db')

def check_foreign_key_integrity(conn: sqlite3.Connection) -> List[Dict]:
    """Check for foreign key constraint violations."""
    cursor = conn.cursor()
    issues = []
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print("\n" + "="*80)
    print("CHECKING FOREIGN KEY INTEGRITY")
    print("="*80)
    
    for table in tables:
        # Check foreign key violations
        cursor.execute(f"PRAGMA foreign_key_check({table})")
        violations = cursor.fetchall()
        
        if violations:
            print(f"\n❌ FOREIGN KEY VIOLATIONS in {table}:")
            for violation in violations:
                print(f"  - Row ID: {violation[0]}, Parent: {violation[1]}, FK Index: {violation[2]}")
                issues.append({
                    'table': table,
                    'type': 'foreign_key_violation',
                    'details': violation
                })
        else:
            print(f"✓ {table}: No foreign key violations")
    
    return issues

def check_table_schema(conn: sqlite3.Connection) -> Dict:
    """Get detailed schema information for all tables."""
    cursor = conn.cursor()
    schema_info = {}
    
    print("\n" + "="*80)
    print("TABLE SCHEMAS AND FOREIGN KEYS")
    print("="*80)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        print(f"\n📋 Table: {table}")
        print("-" * 80)
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        print("  Columns:")
        for col in columns:
            pk_marker = " [PRIMARY KEY]" if col[5] else ""
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"    - {col[1]} ({col[2]}) {nullable}{pk_marker}")
        
        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = cursor.fetchall()
        
        if foreign_keys:
            print("  Foreign Keys:")
            for fk in foreign_keys:
                print(f"    - {fk[3]} -> {fk[2]}.{fk[4]} (ON DELETE {fk[6] or 'NO ACTION'})")
        
        schema_info[table] = {
            'columns': columns,
            'foreign_keys': foreign_keys
        }
    
    return schema_info

def check_relationships_table(conn: sqlite3.Connection) -> List[Dict]:
    """Check relationships table for issues."""
    cursor = conn.cursor()
    issues = []
    
    print("\n" + "="*80)
    print("RELATIONSHIPS TABLE CHECK")
    print("="*80)
    
    # Check for orphaned relationships (references non-existent objects)
    cursor.execute("""
        SELECT r.relationship_id, r.dataset_id, r.from_object_id, r.to_object_id,
               r.from_column, r.to_column
        FROM relationships r
        LEFT JOIN data_objects do_from ON r.from_object_id = do_from.object_id
        WHERE do_from.object_id IS NULL
    """)
    orphaned_from = cursor.fetchall()
    
    if orphaned_from:
        print(f"\n❌ ORPHANED RELATIONSHIPS (from_object_id not found):")
        for rel in orphaned_from:
            print(f"  Rel ID {rel[0]}: from_object_id={rel[2]} doesn't exist")
            issues.append({
                'type': 'orphaned_from_object',
                'relationship_id': rel[0],
                'from_object_id': rel[2]
            })
    
    cursor.execute("""
        SELECT r.relationship_id, r.dataset_id, r.from_object_id, r.to_object_id,
               r.from_column, r.to_column
        FROM relationships r
        LEFT JOIN data_objects do_to ON r.to_object_id = do_to.object_id
        WHERE do_to.object_id IS NULL
    """)
    orphaned_to = cursor.fetchall()
    
    if orphaned_to:
        print(f"\n❌ ORPHANED RELATIONSHIPS (to_object_id not found):")
        for rel in orphaned_to:
            print(f"  Rel ID {rel[0]}: to_object_id={rel[3]} doesn't exist")
            issues.append({
                'type': 'orphaned_to_object',
                'relationship_id': rel[0],
                'to_object_id': rel[3]
            })
    
    # Check for invalid column references
    cursor.execute("""
        SELECT r.relationship_id, r.from_object_id, r.from_column, do.object_name
        FROM relationships r
        JOIN data_objects do ON r.from_object_id = do.object_id
        LEFT JOIN columns c ON c.object_id = r.from_object_id AND c.column_name = r.from_column
        WHERE c.column_id IS NULL
    """)
    invalid_from_cols = cursor.fetchall()
    
    if invalid_from_cols:
        print(f"\n❌ INVALID FROM COLUMN REFERENCES:")
        for rel in invalid_from_cols:
            print(f"  Rel ID {rel[0]}: {rel[3]}.{rel[2]} (column doesn't exist)")
            issues.append({
                'type': 'invalid_from_column',
                'relationship_id': rel[0],
                'table': rel[3],
                'column': rel[2]
            })
    
    cursor.execute("""
        SELECT r.relationship_id, r.to_object_id, r.to_column, do.object_name
        FROM relationships r
        JOIN data_objects do ON r.to_object_id = do.object_id
        LEFT JOIN columns c ON c.object_id = r.to_object_id AND c.column_name = r.to_column
        WHERE c.column_id IS NULL
    """)
    invalid_to_cols = cursor.fetchall()
    
    if invalid_to_cols:
        print(f"\n❌ INVALID TO COLUMN REFERENCES:")
        for rel in invalid_to_cols:
            print(f"  Rel ID {rel[0]}: {rel[3]}.{rel[2]} (column doesn't exist)")
            issues.append({
                'type': 'invalid_to_column',
                'relationship_id': rel[0],
                'table': rel[3],
                'column': rel[2]
            })
    
    # Check for duplicate relationships
    cursor.execute("""
        SELECT dataset_id, from_object_id, from_column, to_object_id, to_column, COUNT(*) as cnt
        FROM relationships
        GROUP BY dataset_id, from_object_id, from_column, to_object_id, to_column
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"\n❌ DUPLICATE RELATIONSHIPS:")
        for dup in duplicates:
            print(f"  Dataset {dup[0]}: from_obj={dup[1]}, from_col={dup[2]}, "
                  f"to_obj={dup[3]}, to_col={dup[4]} (count: {dup[5]})")
            issues.append({
                'type': 'duplicate_relationship',
                'dataset_id': dup[0],
                'count': dup[5]
            })
    
    # Check for relationships referencing non-existent datasets
    cursor.execute("""
        SELECT r.relationship_id, r.dataset_id
        FROM relationships r
        LEFT JOIN datasets d ON r.dataset_id = d.dataset_id
        WHERE d.dataset_id IS NULL
    """)
    orphaned_datasets = cursor.fetchall()
    
    if orphaned_datasets:
        print(f"\n❌ RELATIONSHIPS WITH INVALID DATASET REFERENCES:")
        for rel in orphaned_datasets:
            print(f"  Rel ID {rel[0]}: dataset_id={rel[1]} doesn't exist")
            issues.append({
                'type': 'orphaned_dataset',
                'relationship_id': rel[0],
                'dataset_id': rel[1]
            })
    
    # Get valid relationships summary
    cursor.execute("""
        SELECT r.relationship_id, d.dataset_name, 
               do_from.object_name, r.from_column,
               do_to.object_name, r.to_column,
               r.cardinality, r.is_active
        FROM relationships r
        JOIN datasets d ON r.dataset_id = d.dataset_id
        JOIN data_objects do_from ON r.from_object_id = do_from.object_id
        JOIN data_objects do_to ON r.to_object_id = do_to.object_id
    """)
    valid_rels = cursor.fetchall()
    
    print(f"\n✓ VALID RELATIONSHIPS: {len(valid_rels)}")
    for rel in valid_rels:
        print(f"  [{rel[0]}] {rel[2]}.{rel[3]} -> {rel[4]}.{rel[5]} ({rel[6]}, Active={rel[7]})")
    
    return issues

def check_data_objects(conn: sqlite3.Connection) -> List[Dict]:
    """Check data_objects table for issues."""
    cursor = conn.cursor()
    issues = []
    
    print("\n" + "="*80)
    print("DATA OBJECTS CHECK")
    print("="*80)
    
    # Check for orphaned data objects (no parent dataset)
    cursor.execute("""
        SELECT do.object_id, do.object_name, do.dataset_id
        FROM data_objects do
        LEFT JOIN datasets d ON do.dataset_id = d.dataset_id
        WHERE d.dataset_id IS NULL
    """)
    orphaned_objects = cursor.fetchall()
    
    if orphaned_objects:
        print(f"\n❌ ORPHANED DATA OBJECTS (dataset doesn't exist):")
        for obj in orphaned_objects:
            print(f"  Object ID {obj[0]}: {obj[1]} (dataset_id={obj[2]})")
            issues.append({
                'type': 'orphaned_data_object',
                'object_id': obj[0],
                'object_name': obj[1],
                'dataset_id': obj[2]
            })
    else:
        print("✓ No orphaned data objects")
    
    # Check for objects without columns
    cursor.execute("""
        SELECT do.object_id, do.object_name, COUNT(c.column_id) as col_count
        FROM data_objects do
        LEFT JOIN columns c ON do.object_id = c.object_id
        GROUP BY do.object_id, do.object_name
        HAVING COUNT(c.column_id) = 0
    """)
    objects_no_columns = cursor.fetchall()
    
    if objects_no_columns:
        print(f"\n⚠️  DATA OBJECTS WITHOUT COLUMNS:")
        for obj in objects_no_columns:
            print(f"  Object ID {obj[0]}: {obj[1]}")
            issues.append({
                'type': 'object_no_columns',
                'object_id': obj[0],
                'object_name': obj[1]
            })
    else:
        print("✓ All data objects have columns")
    
    return issues

def check_columns_table(conn: sqlite3.Connection) -> List[Dict]:
    """Check columns table for issues."""
    cursor = conn.cursor()
    issues = []
    
    print("\n" + "="*80)
    print("COLUMNS TABLE CHECK")
    print("="*80)
    
    # Check for orphaned columns (no parent object)
    cursor.execute("""
        SELECT c.column_id, c.column_name, c.object_id
        FROM columns c
        LEFT JOIN data_objects do ON c.object_id = do.object_id
        WHERE do.object_id IS NULL
    """)
    orphaned_columns = cursor.fetchall()
    
    if orphaned_columns:
        print(f"\n❌ ORPHANED COLUMNS (data object doesn't exist):")
        for col in orphaned_columns:
            print(f"  Column ID {col[0]}: {col[1]} (object_id={col[2]})")
            issues.append({
                'type': 'orphaned_column',
                'column_id': col[0],
                'column_name': col[1],
                'object_id': col[2]
            })
    else:
        print("✓ No orphaned columns")
    
    # Check for duplicate columns in same object
    cursor.execute("""
        SELECT object_id, column_name, COUNT(*) as cnt
        FROM columns
        GROUP BY object_id, column_name
        HAVING COUNT(*) > 1
    """)
    duplicate_columns = cursor.fetchall()
    
    if duplicate_columns:
        print(f"\n❌ DUPLICATE COLUMNS IN SAME OBJECT:")
        for dup in duplicate_columns:
            cursor.execute("SELECT object_name FROM data_objects WHERE object_id = ?", (dup[0],))
            obj_name = cursor.fetchone()
            obj_name = obj_name[0] if obj_name else "Unknown"
            print(f"  Object {obj_name} (ID {dup[0]}): column '{dup[1]}' appears {dup[2]} times")
            issues.append({
                'type': 'duplicate_column',
                'object_id': dup[0],
                'object_name': obj_name,
                'column_name': dup[1],
                'count': dup[2]
            })
    else:
        print("✓ No duplicate columns")
    
    return issues

def check_data_sources(conn: sqlite3.Connection) -> List[Dict]:
    """Check data_sources table for issues."""
    cursor = conn.cursor()
    issues = []
    
    print("\n" + "="*80)
    print("DATA SOURCES CHECK")
    print("="*80)
    
    # Check for sources with invalid object_id
    cursor.execute("""
        SELECT ds.source_id, ds.source_name, ds.object_id
        FROM data_sources ds
        WHERE ds.object_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM data_objects WHERE object_id = ds.object_id)
    """)
    invalid_object_sources = cursor.fetchall()
    
    if invalid_object_sources:
        print(f"\n❌ DATA SOURCES WITH INVALID OBJECT_ID:")
        for src in invalid_object_sources:
            print(f"  Source ID {src[0]}: {src[1]} (object_id={src[2]} doesn't exist)")
            issues.append({
                'type': 'invalid_source_object',
                'source_id': src[0],
                'object_id': src[2]
            })
    else:
        print("✓ All data sources have valid object references")
    
    # Check for sources with invalid dataset_id
    cursor.execute("""
        SELECT ds.source_id, ds.source_name, ds.dataset_id
        FROM data_sources ds
        WHERE ds.dataset_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM datasets WHERE dataset_id = ds.dataset_id)
    """)
    invalid_dataset_sources = cursor.fetchall()
    
    if invalid_dataset_sources:
        print(f"\n❌ DATA SOURCES WITH INVALID DATASET_ID:")
        for src in invalid_dataset_sources:
            print(f"  Source ID {src[0]}: {src[1]} (dataset_id={src[2]} doesn't exist)")
            issues.append({
                'type': 'invalid_source_dataset',
                'source_id': src[0],
                'dataset_id': src[2]
            })
    else:
        print("✓ All data sources have valid dataset references")
    
    return issues

def check_measures(conn: sqlite3.Connection) -> List[Dict]:
    """Check measures table for issues."""
    cursor = conn.cursor()
    issues = []
    
    print("\n" + "="*80)
    print("MEASURES CHECK")
    print("="*80)
    
    # Check for orphaned measures
    cursor.execute("""
        SELECT m.measure_id, m.measure_name, m.dataset_id, m.object_id
        FROM measures m
        LEFT JOIN datasets d ON m.dataset_id = d.dataset_id
        WHERE d.dataset_id IS NULL
    """)
    orphaned_measures = cursor.fetchall()
    
    if orphaned_measures:
        print(f"\n❌ ORPHANED MEASURES (dataset doesn't exist):")
        for meas in orphaned_measures:
            print(f"  Measure ID {meas[0]}: {meas[1]} (dataset_id={meas[2]})")
            issues.append({
                'type': 'orphaned_measure_dataset',
                'measure_id': meas[0],
                'dataset_id': meas[2]
            })
    else:
        print("✓ All measures have valid dataset references")
    
    # Check for measures with invalid object_id
    cursor.execute("""
        SELECT m.measure_id, m.measure_name, m.object_id
        FROM measures m
        WHERE m.object_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM data_objects WHERE object_id = m.object_id)
    """)
    invalid_object_measures = cursor.fetchall()
    
    if invalid_object_measures:
        print(f"\n❌ MEASURES WITH INVALID OBJECT_ID:")
        for meas in invalid_object_measures:
            print(f"  Measure ID {meas[0]}: {meas[1]} (object_id={meas[2]} doesn't exist)")
            issues.append({
                'type': 'invalid_measure_object',
                'measure_id': meas[0],
                'object_id': meas[2]
            })
    else:
        print("✓ All measures have valid object references")
    
    return issues

def main():
    """Run comprehensive database check."""
    db_path = get_database_path()
    print(f"Checking database: {db_path}\n")
    
    # Connect with foreign keys enabled
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    
    all_issues = []
    
    try:
        # Run all checks
        all_issues.extend(check_foreign_key_integrity(conn))
        schema_info = check_table_schema(conn)
        all_issues.extend(check_relationships_table(conn))
        all_issues.extend(check_data_objects(conn))
        all_issues.extend(check_columns_table(conn))
        all_issues.extend(check_data_sources(conn))
        all_issues.extend(check_measures(conn))
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        if all_issues:
            print(f"\n❌ TOTAL ISSUES FOUND: {len(all_issues)}")
            
            # Group by type
            issue_types = {}
            for issue in all_issues:
                issue_type = issue['type']
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            
            print("\nIssues by type:")
            for issue_type, count in sorted(issue_types.items()):
                print(f"  - {issue_type}: {count}")
        else:
            print("\n✅ NO ISSUES FOUND - Database integrity is good!")
        
    finally:
        conn.close()
    
    return all_issues

if __name__ == "__main__":
    issues = main()
