"""Dataset data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sqlite3
import json


@dataclass
class Dataset:
    """Represents a dataset/workbook in a BI tool."""
    
    dataset_id: str
    dataset_name: str
    workspace_id: str
    tool_id: str
    dataset_type: Optional[str] = None
    file_path: Optional[str] = None
    compatibility_level: Optional[int] = None
    model_type: Optional[str] = None
    data_access_mode: Optional[str] = None
    tool_specific_metadata: Optional[dict] = None
    last_analyzed: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    size_bytes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def save(self, conn: sqlite3.Connection):
        """Save dataset to database."""
        cursor = conn.cursor()
        
        metadata_json = json.dumps(self.tool_specific_metadata) if self.tool_specific_metadata else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO datasets 
            (dataset_id, dataset_name, workspace_id, tool_id, dataset_type, file_path,
             compatibility_level, model_type, data_access_mode, tool_specific_metadata,
             last_analyzed, last_modified, size_bytes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            self.dataset_id,
            self.dataset_name,
            self.workspace_id,
            self.tool_id,
            self.dataset_type,
            self.file_path,
            self.compatibility_level,
            self.model_type,
            self.data_access_mode,
            metadata_json,
            self.last_analyzed,
            self.last_modified,
            self.size_bytes
        ))
        
        conn.commit()
        
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, dataset_id: str) -> Optional['Dataset']:
        """Retrieve dataset by ID."""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM datasets WHERE dataset_id = ?', (dataset_id,))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            return Dataset(**data)
        return None
        
    @staticmethod
    def get_by_workspace(conn: sqlite3.Connection, workspace_id: str) -> list['Dataset']:
        """Get all datasets in a workspace."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM datasets 
            WHERE workspace_id = ? 
            ORDER BY dataset_name
        ''', (workspace_id,))
        
        datasets = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            datasets.append(Dataset(**data))
        return datasets
        
    @staticmethod
    def search(conn: sqlite3.Connection, 
               search_term: Optional[str] = None,
               tool_id: Optional[str] = None,
               workspace_id: Optional[str] = None,
               limit: int = 100) -> list[dict]:
        """Search datasets with filters."""
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                d.*,
                w.workspace_name,
                COUNT(DISTINCT do.object_id) as object_count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as migration_needed_count
            FROM datasets d
            JOIN workspaces w ON d.workspace_id = w.workspace_id
            LEFT JOIN data_objects do ON d.dataset_id = do.dataset_id
            LEFT JOIN data_sources ds ON do.object_id = ds.object_id
            WHERE 1=1
        '''
        
        params = []
        
        if search_term:
            query += ' AND (d.dataset_name LIKE ? OR w.workspace_name LIKE ?)'
            params.extend([f'%{search_term}%', f'%{search_term}%'])
            
        if tool_id:
            query += ' AND d.tool_id = ?'
            params.append(tool_id)
            
        if workspace_id:
            query += ' AND d.workspace_id = ?'
            params.append(workspace_id)
            
        query += '''
            GROUP BY d.dataset_id
            ORDER BY d.dataset_name
            LIMIT ?
        '''
        params.append(limit)
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    @staticmethod
    def delete(conn: sqlite3.Connection, dataset_id: str):
        """Delete dataset and all related data."""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM datasets WHERE dataset_id = ?', (dataset_id,))
        conn.commit()
