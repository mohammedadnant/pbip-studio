"""
Database schema for multi-tool BI migration support.
Supports Power BI, Tableau, and other BI tools with extensible design.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import json
from datetime import datetime
import os


def get_database_path(db_filename: str = "fabric_migration.db") -> str:
    """
    Get database path in user AppData directory (writable location).
    
    Args:
        db_filename: Name of the database file
        
    Returns:
        Full path to database file in AppData
    """
    try:
        # Use AppData/Local for user-writable location
        appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~/.local/share'))
        db_dir = Path(appdata) / 'PowerBI Migration Toolkit' / 'data'
        
        # Create directory with full permissions
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify directory is writable
        test_file = db_dir / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            print(f"Warning: Directory {db_dir} may not be writable: {e}")
            raise
        
        return str(db_dir / db_filename)
    except Exception as e:
        # Fallback to user's home directory if AppData fails
        print(f"Error accessing AppData, falling back to home directory: {e}")
        home_dir = Path.home() / '.pbip_studio' / 'data'
        home_dir.mkdir(parents=True, exist_ok=True)
        return str(home_dir / db_filename)


class FabricDatabase:
    """Database manager for BI tool migration tracking."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (defaults to AppData location)
        """
        # Use AppData location by default (writable for users)
        if db_path is None:
            db_path = get_database_path()
        
        print(f"Initializing database at: {db_path}")
        self.db_path = db_path
        self.conn = None
        self._connect()
        
    def _connect(self):
        """Establish database connection with proper permissions."""
        try:
            # Ensure parent directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Connect with proper settings
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Enable foreign keys and set journal mode for better concurrency
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            # Use WAL mode only if we have write permissions
            try:
                self.conn.execute("PRAGMA journal_mode = WAL")
            except sqlite3.OperationalError:
                print("Warning: Could not enable WAL mode, using default journal mode")
            
            # Verify database is writable by testing a simple operation
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA user_version")
            cursor.fetchone()
            
            print(f"[OK] Database connection established successfully")
            
        except sqlite3.OperationalError as e:
            print(f"[ERROR] Database connection error: {e}")
            print(f"  Database path: {self.db_path}")
            print(f"  Please ensure the application has write permissions")
            raise
        except Exception as e:
            print(f"[ERROR] Unexpected database error: {e}")
            raise
        
    def initialize_schema(self):
        """Create all database tables and indexes."""
        try:
            cursor = self.conn.cursor()
            
            # BI Tools registry
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bi_tools (
                    tool_id TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    tool_version TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Workspaces (Power BI workspaces, Tableau projects, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    workspace_name TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    parent_workspace_id TEXT,
                    workspace_type TEXT,
                    description TEXT,
                    last_scanned TIMESTAMP,
                    scan_status TEXT,
                    scan_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tool_id) REFERENCES bi_tools(tool_id),
                    FOREIGN KEY (parent_workspace_id) REFERENCES workspaces(workspace_id)
                )
            ''')
            
            # Datasets (Power BI datasets, Tableau workbooks, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY,
                    dataset_name TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    dataset_type TEXT,
                    file_path TEXT,
                    compatibility_level INTEGER,
                    model_type TEXT,
                    data_access_mode TEXT,
                    tool_specific_metadata TEXT,
                    last_analyzed TIMESTAMP,
                    last_modified TIMESTAMP,
                    size_bytes INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
                    FOREIGN KEY (tool_id) REFERENCES bi_tools(tool_id)
                )
            ''')
            
            # Data objects (Tables, Sheets, Views, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_objects (
                    object_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT NOT NULL,
                    object_name TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    schema_name TEXT,
                    partition_count INTEGER,
                    row_count INTEGER,
                    column_count INTEGER,
                    has_partitions BOOLEAN DEFAULT FALSE,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    description TEXT,
                    tool_specific_metadata TEXT,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(dataset_id, object_name),
                    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE
                )
            ''')
            
            # Table columns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS columns (
                    column_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    object_id INTEGER NOT NULL,
                    column_name TEXT NOT NULL,
                    data_type TEXT,
                    is_nullable BOOLEAN,
                    is_key BOOLEAN DEFAULT FALSE,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    format_string TEXT,
                    description TEXT,
                    expression TEXT,
                    source_column TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (object_id) REFERENCES data_objects(object_id) ON DELETE CASCADE,
                    UNIQUE(object_id, column_name)
                )
            ''')
            
            # Data sources
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    object_id INTEGER,
                    dataset_id TEXT,
                    source_type TEXT NOT NULL,
                    source_name TEXT,
                    connection_string TEXT,
                    server TEXT,
                    database_name TEXT,
                    schema_name TEXT,
                    query TEXT,
                    m_expression TEXT,
                    credential_type TEXT,
                    requires_migration BOOLEAN DEFAULT FALSE,
                    migration_priority INTEGER,
                    tool_specific_metadata TEXT,
                    last_tested TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (object_id) REFERENCES data_objects(object_id) ON DELETE CASCADE,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE
                )
            ''')
            
            # Migration history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migration_history (
                    migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT,
                    object_id INTEGER,
                    source_id INTEGER,
                    migration_type TEXT NOT NULL,
                    old_source_type TEXT,
                    new_source_type TEXT,
                    old_connection TEXT,
                    new_connection TEXT,
                    changes_json TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    migrated_by TEXT,
                    rollback_data TEXT,
                    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id),
                    FOREIGN KEY (object_id) REFERENCES data_objects(object_id),
                    FOREIGN KEY (source_id) REFERENCES data_sources(source_id)
                )
            ''')
            
            # Relationships
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT NOT NULL,
                    from_object_id INTEGER NOT NULL,
                    from_column TEXT NOT NULL,
                    to_object_id INTEGER NOT NULL,
                    to_column TEXT NOT NULL,
                    relationship_type TEXT,
                    cardinality TEXT,
                    cross_filter_direction TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(dataset_id, from_object_id, from_column, to_object_id, to_column),
                    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE,
                    FOREIGN KEY (from_object_id) REFERENCES data_objects(object_id),
                    FOREIGN KEY (to_object_id) REFERENCES data_objects(object_id)
                )
            ''')
            
            # Measures
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS measures (
                    measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT NOT NULL,
                    object_id INTEGER,
                    measure_name TEXT NOT NULL,
                    expression TEXT NOT NULL,
                    format_string TEXT,
                    description TEXT,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(dataset_id, object_id, measure_name),
                    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE,
                    FOREIGN KEY (object_id) REFERENCES data_objects(object_id)
                )
            ''')
            
            # Note: table_columns was merged into columns table for consistency
            
            # Power Query M Code
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS power_query (
                    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    object_id INTEGER NOT NULL UNIQUE,
                    m_code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (object_id) REFERENCES data_objects(object_id) ON DELETE CASCADE
                )
            ''')
            
            # Assessment findings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assessment_findings (
                    finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT,
                    object_id INTEGER,
                    finding_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    category TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    recommendation TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    status TEXT DEFAULT 'open',
                    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id),
                    FOREIGN KEY (object_id) REFERENCES data_objects(object_id)
                )
            ''')
            
            # Create indexes
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_workspace_tool ON workspaces(tool_id)',
                'CREATE INDEX IF NOT EXISTS idx_workspace_name ON workspaces(workspace_name)',
                'CREATE INDEX IF NOT EXISTS idx_dataset_workspace ON datasets(workspace_id)',
                'CREATE INDEX IF NOT EXISTS idx_dataset_tool ON datasets(tool_id)',
                'CREATE INDEX IF NOT EXISTS idx_dataset_name ON datasets(dataset_name)',
                'CREATE INDEX IF NOT EXISTS idx_object_dataset ON data_objects(dataset_id)',
                'CREATE INDEX IF NOT EXISTS idx_object_name ON data_objects(object_name)',
                'CREATE INDEX IF NOT EXISTS idx_source_migration ON data_sources(requires_migration)',
            ]
            
            for idx in indexes:
                cursor.execute(idx)
            
            # Commit changes after schema setup completes
            self.conn.commit()
            print("✓ Database schema initialized successfully")
            
            self._initialize_bi_tools()
            
        except sqlite3.OperationalError as e:
            self.conn.rollback()
            print(f"✗ Schema initialization error: {e}")
            raise
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Unexpected error during schema initialization: {e}")
            raise
        
    def _initialize_bi_tools(self):
        """Initialize default BI tools."""
        try:
            cursor = self.conn.cursor()
            
            tools = [
                ('powerbi', 'Microsoft Power BI', None, 'Power BI Desktop and Fabric'),
            ]
            
            for tool in tools:
                cursor.execute('''
                    INSERT OR IGNORE INTO bi_tools (tool_id, tool_name, tool_version, description)
                    VALUES (?, ?, ?, ?)
                ''', tool)
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            print(f"Warning: Could not initialize BI tools: {e}")
        
    def get_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        stats = {}
        
        tables = ['workspaces', 'datasets', 'data_objects', 'data_sources']
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        
        return stats
    
    def clear_all_data(self):
        """Clear all data from tables (truncate). Keeps schema intact."""
        cursor = self.conn.cursor()
        
        # List of tables to clear (in order to respect foreign keys)
        tables = [
            'migration_history',
            'columns',
            'measures',
            'relationships',
            'power_query',
            'data_sources',
            'data_objects',
            'datasets',
            'workspaces',
            'bi_tools'
        ]
        
        try:
            # Disable foreign keys temporarily for faster delete
            cursor.execute('PRAGMA foreign_keys = OFF')
            
            for table in tables:
                cursor.execute(f'DELETE FROM {table}')
            
            # Reset auto-increment counters
            cursor.execute('DELETE FROM sqlite_sequence')
            
            self.conn.commit()
            
            # Re-enable foreign keys
            cursor.execute('PRAGMA foreign_keys = ON')
            
            print(f"✓ Database cleared - all tables truncated")
            
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error clearing database: {e}")
            raise
    
    def get_database_location(self) -> str:
        """
        Get the current database file location.
        
        Returns:
            Full path to the database file
        """
        return self.db_path
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

