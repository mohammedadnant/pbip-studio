"""Workspace data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import sqlite3


@dataclass
class Workspace:
    """Represents a workspace/project container in a BI tool."""
    
    workspace_id: str
    workspace_name: str
    tool_id: str
    parent_workspace_id: Optional[str] = None
    workspace_type: Optional[str] = None
    description: Optional[str] = None
    last_scanned: Optional[datetime] = None
    scan_status: Optional[str] = None
    scan_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def save(self, conn: sqlite3.Connection):
        """Save workspace to database."""
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO workspaces 
            (workspace_id, workspace_name, tool_id, parent_workspace_id, workspace_type, 
             description, last_scanned, scan_status, scan_error, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            self.workspace_id,
            self.workspace_name,
            self.tool_id,
            self.parent_workspace_id,
            self.workspace_type,
            self.description,
            self.last_scanned,
            self.scan_status,
            self.scan_error
        ))
        
        conn.commit()
        
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, workspace_id: str) -> Optional['Workspace']:
        """Retrieve workspace by ID."""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workspaces WHERE workspace_id = ?', (workspace_id,))
        row = cursor.fetchone()
        
        if row:
            return Workspace(**dict(row))
        return None
        
    @staticmethod
    def get_all(conn: sqlite3.Connection, tool_id: Optional[str] = None) -> list['Workspace']:
        """Get all workspaces, optionally filtered by tool."""
        cursor = conn.cursor()
        
        if tool_id:
            cursor.execute('SELECT * FROM workspaces WHERE tool_id = ? ORDER BY workspace_name', (tool_id,))
        else:
            cursor.execute('SELECT * FROM workspaces ORDER BY workspace_name')
            
        return [Workspace(**dict(row)) for row in cursor.fetchall()]
        
    @staticmethod
    def delete(conn: sqlite3.Connection, workspace_id: str):
        """Delete workspace and all related data."""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workspaces WHERE workspace_id = ?', (workspace_id,))
        conn.commit()
