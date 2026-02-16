"""Data source (connection) data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sqlite3
import json


@dataclass
class DataSource:
    """Represents a data source/connection."""
    
    source_id: Optional[int]
    object_id: Optional[int]
    dataset_id: Optional[str]
    source_type: str
    source_name: Optional[str] = None
    connection_string: Optional[str] = None
    server: Optional[str] = None
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    query: Optional[str] = None
    m_expression: Optional[str] = None
    credential_type: Optional[str] = None
    requires_migration: bool = False
    migration_priority: Optional[int] = None
    tool_specific_metadata: Optional[dict] = None
    last_tested: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def save(self, conn: sqlite3.Connection) -> int:
        """Save data source to database and return source_id."""
        cursor = conn.cursor()
        
        metadata_json = json.dumps(self.tool_specific_metadata) if self.tool_specific_metadata else None
        
        if self.source_id:
            cursor.execute('''
                UPDATE data_sources 
                SET object_id = ?, dataset_id = ?, source_type = ?, source_name = ?,
                    connection_string = ?, server = ?, database_name = ?, schema_name = ?,
                    query = ?, m_expression = ?, credential_type = ?,
                    requires_migration = ?, migration_priority = ?,
                    tool_specific_metadata = ?, last_tested = ?
                WHERE source_id = ?
            ''', (
                self.object_id, self.dataset_id, self.source_type, self.source_name,
                self.connection_string, self.server, self.database_name, self.schema_name,
                self.query, self.m_expression, self.credential_type,
                self.requires_migration, self.migration_priority,
                metadata_json, self.last_tested, self.source_id
            ))
            source_id = self.source_id
        else:
            cursor.execute('''
                INSERT INTO data_sources 
                (object_id, dataset_id, source_type, source_name, connection_string,
                 server, database_name, schema_name, query, m_expression, credential_type,
                 requires_migration, migration_priority, tool_specific_metadata, last_tested)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.object_id, self.dataset_id, self.source_type, self.source_name,
                self.connection_string, self.server, self.database_name, self.schema_name,
                self.query, self.m_expression, self.credential_type,
                self.requires_migration, self.migration_priority,
                metadata_json, self.last_tested
            ))
            source_id = cursor.lastrowid
            self.source_id = source_id
            
        conn.commit()
        return source_id
        
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, source_id: int) -> Optional['DataSource']:
        """Retrieve data source by ID."""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM data_sources WHERE source_id = ?', (source_id,))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            return DataSource(**data)
        return None
        
    @staticmethod
    def get_by_object(conn: sqlite3.Connection, object_id: int) -> list['DataSource']:
        """Get all data sources for a data object."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM data_sources 
            WHERE object_id = ? 
            ORDER BY source_type
        ''', (object_id,))
        
        sources = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            sources.append(DataSource(**data))
        return sources
        
    @staticmethod
    def get_by_dataset(conn: sqlite3.Connection, dataset_id: str) -> list['DataSource']:
        """Get all data sources for a dataset."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ds.* FROM data_sources ds
            LEFT JOIN data_objects do ON ds.object_id = do.object_id
            WHERE ds.dataset_id = ? OR do.dataset_id = ?
            ORDER BY ds.source_type
        ''', (dataset_id, dataset_id))
        
        sources = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            sources.append(DataSource(**data))
        return sources
        
    @staticmethod
    def get_migration_candidates(conn: sqlite3.Connection,
                                 dataset_id: Optional[str] = None,
                                 workspace_id: Optional[str] = None) -> list[dict]:
        """Get data sources that need migration."""
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                ds.*,
                do.object_name,
                d.dataset_name,
                w.workspace_name
            FROM data_sources ds
            LEFT JOIN data_objects do ON ds.object_id = do.object_id
            LEFT JOIN datasets d ON do.dataset_id = d.dataset_id OR ds.dataset_id = d.dataset_id
            LEFT JOIN workspaces w ON d.workspace_id = w.workspace_id
            WHERE ds.requires_migration = 1
        '''
        
        params = []
        
        if dataset_id:
            query += ' AND (ds.dataset_id = ? OR do.dataset_id = ?)'
            params.extend([dataset_id, dataset_id])
            
        if workspace_id:
            query += ' AND w.workspace_id = ?'
            params.append(workspace_id)
            
        query += ' ORDER BY ds.migration_priority DESC, ds.source_type'
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    @staticmethod
    def get_source_type_summary(conn: sqlite3.Connection) -> list[dict]:
        """Get summary of data sources by type."""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                source_type,
                COUNT(*) as total_count,
                SUM(CASE WHEN requires_migration THEN 1 ELSE 0 END) as migration_needed_count
            FROM data_sources
            GROUP BY source_type
            ORDER BY total_count DESC
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
        
    @staticmethod
    def delete(conn: sqlite3.Connection, source_id: int):
        """Delete data source."""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM data_sources WHERE source_id = ?', (source_id,))
        conn.commit()
