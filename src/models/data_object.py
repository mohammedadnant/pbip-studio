"""Data object (table/sheet/view) data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sqlite3
import json


@dataclass
class DataObject:
    """Represents a table, sheet, or view in a dataset."""
    
    object_id: Optional[int]
    dataset_id: str
    object_name: str
    object_type: str
    schema_name: Optional[str] = None
    partition_count: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    has_partitions: bool = False
    is_hidden: bool = False
    description: Optional[str] = None
    tool_specific_metadata: Optional[dict] = None
    last_modified: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def save(self, conn: sqlite3.Connection) -> int:
        """Save data object to database and return object_id."""
        cursor = conn.cursor()
        
        metadata_json = json.dumps(self.tool_specific_metadata) if self.tool_specific_metadata else None
        
        if self.object_id:
            cursor.execute('''
                UPDATE data_objects 
                SET object_name = ?, object_type = ?, schema_name = ?,
                    partition_count = ?, row_count = ?, column_count = ?,
                    has_partitions = ?, is_hidden = ?, description = ?,
                    tool_specific_metadata = ?, last_modified = ?
                WHERE object_id = ?
            ''', (
                self.object_name, self.object_type, self.schema_name,
                self.partition_count, self.row_count, self.column_count,
                self.has_partitions, self.is_hidden, self.description,
                metadata_json, self.last_modified, self.object_id
            ))
            object_id = self.object_id
        else:
            # Check if object already exists (by dataset_id + object_name)
            cursor.execute('''
                SELECT object_id FROM data_objects 
                WHERE dataset_id = ? AND object_name = ?
            ''', (self.dataset_id, self.object_name))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing object
                object_id = existing[0]
                self.object_id = object_id
                cursor.execute('''
                    UPDATE data_objects 
                    SET object_type = ?, schema_name = ?,
                        partition_count = ?, row_count = ?, column_count = ?,
                        has_partitions = ?, is_hidden = ?, description = ?,
                        tool_specific_metadata = ?, last_modified = ?
                    WHERE object_id = ?
                ''', (
                    self.object_type, self.schema_name,
                    self.partition_count, self.row_count, self.column_count,
                    self.has_partitions, self.is_hidden, self.description,
                    metadata_json, self.last_modified, object_id
                ))
            else:
                # Insert new object
                cursor.execute('''
                    INSERT INTO data_objects 
                    (dataset_id, object_name, object_type, schema_name, partition_count,
                     row_count, column_count, has_partitions, is_hidden, description,
                     tool_specific_metadata, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.dataset_id, self.object_name, self.object_type, self.schema_name,
                    self.partition_count, self.row_count, self.column_count,
                    self.has_partitions, self.is_hidden, self.description,
                    metadata_json, self.last_modified
                ))
                object_id = cursor.lastrowid
                self.object_id = object_id
            
        conn.commit()
        return object_id
        
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, object_id: int) -> Optional['DataObject']:
        """Retrieve data object by ID."""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM data_objects WHERE object_id = ?', (object_id,))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            return DataObject(**data)
        return None
        
    @staticmethod
    def get_by_dataset(conn: sqlite3.Connection, dataset_id: str) -> list['DataObject']:
        """Get all data objects in a dataset."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM data_objects 
            WHERE dataset_id = ? 
            ORDER BY object_name
        ''', (dataset_id,))
        
        objects = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            objects.append(DataObject(**data))
        return objects
        
    @staticmethod
    def search_by_name(conn: sqlite3.Connection, 
                       search_term: str,
                       dataset_id: Optional[str] = None) -> list['DataObject']:
        """Search data objects by name."""
        cursor = conn.cursor()
        
        if dataset_id:
            cursor.execute('''
                SELECT * FROM data_objects 
                WHERE object_name LIKE ? AND dataset_id = ?
                ORDER BY object_name
            ''', (f'%{search_term}%', dataset_id))
        else:
            cursor.execute('''
                SELECT * FROM data_objects 
                WHERE object_name LIKE ?
                ORDER BY object_name
            ''', (f'%{search_term}%',))
        
        objects = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('tool_specific_metadata'):
                data['tool_specific_metadata'] = json.loads(data['tool_specific_metadata'])
            objects.append(DataObject(**data))
        return objects
        
    @staticmethod
    def delete(conn: sqlite3.Connection, object_id: int):
        """Delete data object and all related data."""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM data_objects WHERE object_id = ?', (object_id,))
        conn.commit()
