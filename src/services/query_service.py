"""Query service for searching and retrieving BI metadata."""

import sqlite3
from typing import List, Dict, Optional
from database.schema import FabricDatabase
from models import Workspace, Dataset, DataObject, DataSource


class QueryService:
    """Service for querying BI metadata from database."""
    
    def __init__(self, db: FabricDatabase):
        """
        Initialize query service.
        
        Args:
            db: Database instance
        """
        self.db = db
        
    def search_datasets(self, 
                       search_term: Optional[str] = None,
                       workspace_id: Optional[str] = None,
                       tool_id: Optional[str] = None,
                       requires_migration: Optional[bool] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Dict]:
        """
        Search datasets with filters and aggregates.
        
        Args:
            search_term: Search in dataset/workspace names
            workspace_id: Filter by workspace
            tool_id: Filter by BI tool
            requires_migration: Filter by migration needs
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of dataset dictionaries with aggregates
        """
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT 
                d.dataset_id,
                d.dataset_name,
                d.workspace_id,
                d.tool_id,
                d.dataset_type,
                d.compatibility_level,
                d.size_bytes,
                d.last_analyzed,
                w.workspace_name,
                COUNT(DISTINCT do.object_id) as table_count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as migration_needed_count,
                COUNT(DISTINCT ds.source_id) as total_sources
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
            
        if workspace_id:
            query += ' AND d.workspace_id = ?'
            params.append(workspace_id)
            
        if tool_id:
            query += ' AND d.tool_id = ?'
            params.append(tool_id)
            
        if requires_migration is not None:
            if requires_migration:
                query += ' AND EXISTS (SELECT 1 FROM data_sources ds2 WHERE ds2.dataset_id = d.dataset_id AND ds2.requires_migration = 1)'
            else:
                query += ' AND NOT EXISTS (SELECT 1 FROM data_sources ds2 WHERE ds2.dataset_id = d.dataset_id AND ds2.requires_migration = 1)'
            
        query += '''
            GROUP BY d.dataset_id
            ORDER BY d.dataset_name
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_dataset_details(self, dataset_id: str) -> Optional[Dict]:
        """
        Get detailed information about a dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dataset details dictionary
        """
        dataset = Dataset.get_by_id(self.db.conn, dataset_id)
        if not dataset:
            return None
            
        cursor = self.db.conn.cursor()
        
        # Get workspace info
        cursor.execute('''
            SELECT workspace_name, tool_id
            FROM workspaces
            WHERE workspace_id = ?
        ''', (dataset.workspace_id,))
        ws_row = cursor.fetchone()
        
        # Get tables with source info
        cursor.execute('''
            SELECT 
                do.object_id,
                do.object_name,
                do.object_type,
                do.column_count,
                do.partition_count,
                do.is_hidden,
                COUNT(DISTINCT ds.source_id) as source_count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as migration_needed
            FROM data_objects do
            LEFT JOIN data_sources ds ON do.object_id = ds.object_id
            WHERE do.dataset_id = ?
            GROUP BY do.object_id
            ORDER BY do.object_name
        ''', (dataset_id,))
        
        tables = [dict(row) for row in cursor.fetchall()]
        
        # Get data source summary
        cursor.execute('''
            SELECT 
                ds.source_type,
                COUNT(*) as count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as needs_migration
            FROM data_sources ds
            LEFT JOIN data_objects do ON ds.object_id = do.object_id
            WHERE ds.dataset_id = ? OR do.dataset_id = ?
            GROUP BY ds.source_type
        ''', (dataset_id, dataset_id))
        
        source_summary = [dict(row) for row in cursor.fetchall()]
        
        return {
            'dataset': dataset.__dict__,
            'workspace_name': ws_row[0] if ws_row else 'Unknown',
            'tool_id': ws_row[1] if ws_row else 'Unknown',
            'tables': tables,
            'source_summary': source_summary
        }
        
    def get_workspaces(self, tool_id: Optional[str] = None) -> List[Dict]:
        """
        Get all workspaces with statistics.
        
        Args:
            tool_id: Filter by BI tool
            
        Returns:
            List of workspace dictionaries with stats
        """
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT 
                w.workspace_id,
                w.workspace_name,
                w.tool_id,
                w.last_scanned,
                w.scan_status,
                COUNT(DISTINCT d.dataset_id) as dataset_count,
                COUNT(DISTINCT do.object_id) as table_count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as migration_needed_count
            FROM workspaces w
            LEFT JOIN datasets d ON w.workspace_id = d.workspace_id
            LEFT JOIN data_objects do ON d.dataset_id = do.dataset_id
            LEFT JOIN data_sources ds ON do.object_id = ds.object_id
        '''
        
        params = []
        if tool_id:
            query += ' WHERE w.tool_id = ?'
            params.append(tool_id)
            
        query += '''
            GROUP BY w.workspace_id
            ORDER BY w.workspace_name
        '''
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_migration_candidates(self, 
                                 workspace_id: Optional[str] = None,
                                 dataset_id: Optional[str] = None,
                                 source_type: Optional[str] = None) -> List[Dict]:
        """
        Get data sources that need migration.
        
        Args:
            workspace_id: Filter by workspace
            dataset_id: Filter by dataset
            source_type: Filter by source type
            
        Returns:
            List of migration candidate dictionaries
        """
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT 
                ds.source_id,
                ds.source_type,
                ds.source_name,
                ds.server,
                ds.database_name,
                ds.connection_string,
                ds.migration_priority,
                do.object_id,
                do.object_name,
                d.dataset_id,
                d.dataset_name,
                w.workspace_id,
                w.workspace_name,
                w.tool_id
            FROM data_sources ds
            LEFT JOIN data_objects do ON ds.object_id = do.object_id
            LEFT JOIN datasets d ON (ds.dataset_id = d.dataset_id OR do.dataset_id = d.dataset_id)
            LEFT JOIN workspaces w ON d.workspace_id = w.workspace_id
            WHERE ds.requires_migration = 1
        '''
        
        params = []
        
        if workspace_id:
            query += ' AND w.workspace_id = ?'
            params.append(workspace_id)
            
        if dataset_id:
            query += ' AND d.dataset_id = ?'
            params.append(dataset_id)
            
        if source_type:
            query += ' AND ds.source_type = ?'
            params.append(source_type)
            
        query += ' ORDER BY ds.migration_priority DESC, ds.source_type, do.object_name'
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_data_source_summary(self, tool_id: Optional[str] = None) -> List[Dict]:
        """
        Get summary of data sources by type.
        
        Args:
            tool_id: Filter by BI tool
            
        Returns:
            List of source type summary dictionaries
        """
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT 
                ds.source_type,
                COUNT(DISTINCT ds.source_id) as total_count,
                COUNT(DISTINCT do.dataset_id) as dataset_count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as migration_needed_count
            FROM data_sources ds
            LEFT JOIN data_objects do ON ds.object_id = do.object_id
            LEFT JOIN datasets d ON (ds.dataset_id = d.dataset_id OR do.dataset_id = d.dataset_id)
            LEFT JOIN workspaces w ON d.workspace_id = w.workspace_id
        '''
        
        params = []
        if tool_id:
            query += ' WHERE w.tool_id = ?'
            params.append(tool_id)
            
        query += '''
            GROUP BY ds.source_type
            ORDER BY total_count DESC
        '''
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    def search_tables(self, 
                     search_term: str,
                     dataset_id: Optional[str] = None,
                     workspace_id: Optional[str] = None) -> List[Dict]:
        """
        Search for tables/data objects.
        
        Args:
            search_term: Search term for table names
            dataset_id: Filter by dataset
            workspace_id: Filter by workspace
            
        Returns:
            List of table dictionaries
        """
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT 
                do.object_id,
                do.object_name,
                do.object_type,
                do.column_count,
                do.is_hidden,
                d.dataset_id,
                d.dataset_name,
                w.workspace_id,
                w.workspace_name,
                COUNT(DISTINCT ds.source_id) as source_count
            FROM data_objects do
            JOIN datasets d ON do.dataset_id = d.dataset_id
            JOIN workspaces w ON d.workspace_id = w.workspace_id
            LEFT JOIN data_sources ds ON do.object_id = ds.object_id
            WHERE do.object_name LIKE ?
        '''
        
        params = [f'%{search_term}%']
        
        if dataset_id:
            query += ' AND do.dataset_id = ?'
            params.append(dataset_id)
            
        if workspace_id:
            query += ' AND w.workspace_id = ?'
            params.append(workspace_id)
            
        query += '''
            GROUP BY do.object_id
            ORDER BY do.object_name
            LIMIT 100
        '''
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_table_details(self, object_id: int) -> Optional[Dict]:
        """
        Get detailed information about a table.
        
        Args:
            object_id: Data object identifier
            
        Returns:
            Table details dictionary
        """
        data_object = DataObject.get_by_id(self.db.conn, object_id)
        if not data_object:
            return None
            
        # Get data sources
        data_sources = DataSource.get_by_object(self.db.conn, object_id)
        
        # Get columns
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM columns
            WHERE object_id = ?
            ORDER BY column_name
        ''', (object_id,))
        
        columns = [dict(row) for row in cursor.fetchall()]
        
        # Get dataset info
        dataset = Dataset.get_by_id(self.db.conn, data_object.dataset_id)
        
        return {
            'table': data_object.__dict__,
            'dataset': dataset.__dict__ if dataset else None,
            'data_sources': [ds.__dict__ for ds in data_sources],
            'columns': columns
        }
        
    def get_statistics(self) -> Dict:
        """Get overall database statistics."""
        return self.db.get_stats()
    
    def get_assessment_summary(self) -> Dict:
        """
        Get comprehensive assessment summary for management dashboard.
        
        Returns:
            Dictionary with executive KPIs and analytics
        """
        cursor = self.db.conn.cursor()
        
        # Total counts
        cursor.execute('SELECT COUNT(*) FROM workspaces')
        total_workspaces = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM datasets')
        total_datasets = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM data_objects WHERE object_type = "Table"')
        total_tables = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT source_id) FROM data_sources')
        total_data_sources = cursor.fetchone()[0]
        
        # Migration needs
        cursor.execute('''
            SELECT COUNT(DISTINCT dataset_id) 
            FROM data_sources 
            WHERE requires_migration = 1
        ''')
        datasets_needing_migration = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM data_sources 
            WHERE requires_migration = 1
        ''')
        sources_needing_migration = cursor.fetchone()[0]
        
        # Data source breakdown
        cursor.execute('''
            SELECT source_type, COUNT(DISTINCT source_id) as count
            FROM data_sources
            GROUP BY source_type
            ORDER BY count DESC
        ''')
        source_distribution = [dict(row) for row in cursor.fetchall()]
        
        # Migration readiness (complexity scoring)
        cursor.execute('''
            SELECT 
                d.dataset_id,
                d.dataset_name,
                w.workspace_name,
                COUNT(DISTINCT do.object_id) as table_count,
                COUNT(DISTINCT ds.source_id) as source_count,
                SUM(CASE WHEN ds.requires_migration THEN 1 ELSE 0 END) as migration_count
            FROM datasets d
            LEFT JOIN workspaces w ON d.workspace_id = w.workspace_id
            LEFT JOIN data_objects do ON d.dataset_id = do.dataset_id
            LEFT JOIN data_sources ds ON do.object_id = ds.object_id
            GROUP BY d.dataset_id
        ''')
        datasets_analysis = [dict(row) for row in cursor.fetchall()]
        
        # Get source types for each dataset
        for dataset in datasets_analysis:
            cursor.execute('''
                SELECT DISTINCT ds.source_type
                FROM data_sources ds
                INNER JOIN data_objects do ON ds.object_id = do.object_id
                WHERE do.dataset_id = ?
                AND ds.source_type IS NOT NULL
                ORDER BY ds.source_type
            ''', (dataset['dataset_id'],))
            source_types = [row[0] for row in cursor.fetchall() if row[0]]
            dataset['source_types'] = source_types
        
        # Calculate complexity scores
        high_complexity = 0
        medium_complexity = 0
        low_complexity = 0
        
        for ds in datasets_analysis:
            tables = ds.get('table_count', 0)
            sources = ds.get('source_count', 0)
            migrations = ds.get('migration_count', 0)
            
            if migrations > 5 or tables > 20:
                high_complexity += 1
            elif migrations > 2 or tables > 10:
                medium_complexity += 1
            else:
                low_complexity += 1
        
        # Workspace distribution
        cursor.execute('''
            SELECT w.workspace_name, COUNT(DISTINCT d.dataset_id) as dataset_count
            FROM workspaces w
            LEFT JOIN datasets d ON w.workspace_id = d.workspace_id
            GROUP BY w.workspace_id
            ORDER BY dataset_count DESC
            LIMIT 10
        ''')
        top_workspaces = [dict(row) for row in cursor.fetchall()]
        
        return {
            'overview': {
                'total_workspaces': total_workspaces,
                'total_datasets': total_datasets,
                'total_tables': total_tables,
                'total_data_sources': total_data_sources,
                'datasets_needing_migration': datasets_needing_migration,
                'sources_needing_migration': sources_needing_migration
            },
            'migration_readiness': {
                'high_complexity': high_complexity,
                'medium_complexity': medium_complexity,
                'low_complexity': low_complexity
            },
            'source_distribution': source_distribution,
            'top_workspaces': top_workspaces,
            'datasets_analysis': datasets_analysis
        }
