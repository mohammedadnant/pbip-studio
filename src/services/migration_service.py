"""Migration service for data source transformations."""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime

from database.schema import FabricDatabase
from models import DataSource


class MigrationService:
    """Service for managing data source migrations."""
    
    def __init__(self, db: FabricDatabase):
        """
        Initialize migration service.
        
        Args:
            db: Database instance
        """
        self.db = db
        
    def log_migration(self, 
                     source_id: int,
                     migration_type: str,
                     old_connection: str,
                     new_connection: str,
                     changes: Dict,
                     status: str,
                     migrated_by: str = 'system',
                     error_message: Optional[str] = None) -> int:
        """
        Log a migration operation.
        
        Args:
            source_id: Data source identifier
            migration_type: Type of migration
            old_connection: Original connection string
            new_connection: New connection string
            changes: Dictionary of changes made
            status: Migration status ('success', 'failed', 'pending')
            migrated_by: User/system identifier
            error_message: Error message if failed
            
        Returns:
            Migration record ID
        """
        cursor = self.db.conn.cursor()
        
        # Get data source details
        data_source = DataSource.get_by_id(self.db.conn, source_id)
        if not data_source:
            raise ValueError(f"Data source {source_id} not found")
            
        cursor.execute('''
            INSERT INTO migration_history 
            (dataset_id, object_id, source_id, migration_type, old_source_type,
             new_source_type, old_connection, new_connection, changes_json,
             status, error_message, migrated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data_source.dataset_id,
            data_source.object_id,
            source_id,
            migration_type,
            data_source.source_type,
            changes.get('new_source_type', data_source.source_type),
            old_connection,
            new_connection,
            json.dumps(changes),
            status,
            error_message,
            migrated_by
        ))
        
        migration_id = cursor.lastrowid
        self.db.conn.commit()
        
        return migration_id
        
    def update_data_source(self, 
                          source_id: int,
                          new_connection: Dict,
                          migrated_by: str = 'system') -> bool:
        """
        Update data source with new connection details.
        
        Args:
            source_id: Data source identifier
            new_connection: Dictionary with new connection details
            migrated_by: User/system identifier
            
        Returns:
            True if successful
        """
        data_source = DataSource.get_by_id(self.db.conn, source_id)
        if not data_source:
            return False
            
        old_connection = data_source.connection_string or ''
        
        # Update data source
        cursor = self.db.conn.cursor()
        
        updates = []
        params = []
        
        if 'source_type' in new_connection:
            updates.append('source_type = ?')
            params.append(new_connection['source_type'])
            
        if 'server' in new_connection:
            updates.append('server = ?')
            params.append(new_connection['server'])
            
        if 'database_name' in new_connection:
            updates.append('database_name = ?')
            params.append(new_connection['database_name'])
            
        if 'connection_string' in new_connection:
            updates.append('connection_string = ?')
            params.append(new_connection['connection_string'])
            
        if 'm_expression' in new_connection:
            updates.append('m_expression = ?')
            params.append(new_connection['m_expression'])
            
        if 'requires_migration' in new_connection:
            updates.append('requires_migration = ?')
            params.append(new_connection['requires_migration'])
            
        if updates:
            params.append(source_id)
            cursor.execute(
                f"UPDATE data_sources SET {', '.join(updates)} WHERE source_id = ?",
                params
            )
            
            self.db.conn.commit()
            
            # Log migration
            self.log_migration(
                source_id=source_id,
                migration_type='connection_update',
                old_connection=old_connection,
                new_connection=new_connection.get('connection_string', ''),
                changes=new_connection,
                status='success',
                migrated_by=migrated_by
            )
            
            return True
            
        return False
        
    def get_migration_history(self, 
                             dataset_id: Optional[str] = None,
                             source_id: Optional[int] = None,
                             limit: int = 100) -> List[Dict]:
        """
        Get migration history.
        
        Args:
            dataset_id: Filter by dataset
            source_id: Filter by data source
            limit: Maximum results
            
        Returns:
            List of migration records
        """
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT 
                mh.*,
                ds.source_type as current_source_type,
                ds.source_name,
                do.object_name,
                d.dataset_name,
                w.workspace_name
            FROM migration_history mh
            LEFT JOIN data_sources ds ON mh.source_id = ds.source_id
            LEFT JOIN data_objects do ON mh.object_id = do.object_id
            LEFT JOIN datasets d ON mh.dataset_id = d.dataset_id
            LEFT JOIN workspaces w ON d.workspace_id = w.workspace_id
            WHERE 1=1
        '''
        
        params = []
        
        if dataset_id:
            query += ' AND mh.dataset_id = ?'
            params.append(dataset_id)
            
        if source_id:
            query += ' AND mh.source_id = ?'
            params.append(source_id)
            
        query += '''
            ORDER BY mh.migrated_at DESC
            LIMIT ?
        '''
        params.append(limit)
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_migration_stats(self) -> Dict:
        """Get migration statistics."""
        cursor = self.db.conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_migrations,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM migration_history
        ''')
        
        overall = dict(cursor.fetchone())
        
        # By migration type
        cursor.execute('''
            SELECT 
                migration_type,
                COUNT(*) as count,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful
            FROM migration_history
            GROUP BY migration_type
            ORDER BY count DESC
        ''')
        
        by_type = [dict(row) for row in cursor.fetchall()]
        
        # Recent migrations
        cursor.execute('''
            SELECT 
                COUNT(*) as count
            FROM migration_history
            WHERE migrated_at >= datetime('now', '-7 days')
        ''')
        
        recent = cursor.fetchone()[0]
        
        return {
            'overall': overall,
            'by_type': by_type,
            'recent_7_days': recent
        }
        
    def mark_as_migrated(self, source_id: int, migrated_by: str = 'system') -> bool:
        """
        Mark a data source as migrated (no longer requires migration).
        
        Args:
            source_id: Data source identifier
            migrated_by: User/system identifier
            
        Returns:
            True if successful
        """
        data_source = DataSource.get_by_id(self.db.conn, source_id)
        if not data_source:
            return False
            
        cursor = self.db.conn.cursor()
        cursor.execute('''
            UPDATE data_sources
            SET requires_migration = 0
            WHERE source_id = ?
        ''', (source_id,))
        
        self.db.conn.commit()
        
        # Log migration
        self.log_migration(
            source_id=source_id,
            migration_type='mark_completed',
            old_connection=data_source.connection_string or '',
            new_connection=data_source.connection_string or '',
            changes={'requires_migration': False},
            status='success',
            migrated_by=migrated_by
        )
        
        return True
        
    def rollback_migration(self, migration_id: int) -> bool:
        """
        Rollback a migration (placeholder for future implementation).
        
        Args:
            migration_id: Migration record identifier
            
        Returns:
            True if successful
        """
        # TODO: Implement rollback logic using rollback_data field
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM migration_history WHERE migration_id = ?
        ''', (migration_id,))
        
        migration = cursor.fetchone()
        if not migration:
            return False
            
        # For now, just mark as rolled back
        cursor.execute('''
            UPDATE migration_history
            SET status = 'rolled_back'
            WHERE migration_id = ?
        ''', (migration_id,))
        
        self.db.conn.commit()
        
        return True
        
    def get_source_migration_suggestions(self, source_id: int) -> Dict:
        """
        Get migration suggestions for a data source.
        
        Args:
            source_id: Data source identifier
            
        Returns:
            Dictionary with migration suggestions
        """
        data_source = DataSource.get_by_id(self.db.conn, source_id)
        if not data_source:
            return {}
            
        suggestions = {
            'source_id': source_id,
            'current_type': data_source.source_type,
            'suggestions': []
        }
        
        # SQL Server to Azure SQL suggestions
        if data_source.source_type == 'SQL Server' and data_source.server:
            if 'database.windows.net' not in data_source.server.lower():
                suggestions['suggestions'].append({
                    'target_type': 'Azure SQL Database',
                    'description': 'Migrate to Azure SQL Database for cloud-native performance',
                    'priority': 'high',
                    'steps': [
                        'Provision Azure SQL Database',
                        'Migrate schema using Azure Data Studio',
                        'Migrate data using Azure Database Migration Service',
                        'Update connection string to *.database.windows.net'
                    ]
                })
                
        # Excel to Azure Blob/DataLake suggestions
        elif data_source.source_type == 'Excel':
            suggestions['suggestions'].append({
                'target_type': 'Azure Data Lake Storage',
                'description': 'Store Excel files in Azure Data Lake for scalability',
                'priority': 'medium',
                'steps': [
                    'Create Azure Storage Account',
                    'Upload Excel files to blob storage',
                    'Update M query to use Web.Contents with storage URL',
                    'Configure authentication (SAS token or OAuth)'
                ]
            })
            
        # SharePoint to OneLake suggestions
        elif 'SharePoint' in data_source.source_type:
            suggestions['suggestions'].append({
                'target_type': 'OneLake',
                'description': 'Use OneLake shortcut for SharePoint data',
                'priority': 'medium',
                'steps': [
                    'Create OneLake shortcut to SharePoint folder',
                    'Update semantic model to use OneLake path',
                    'Test data refresh in Fabric'
                ]
            })
            
        return suggestions
