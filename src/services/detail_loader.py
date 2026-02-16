"""Service for loading table details from database."""

from database.schema import FabricDatabase
from typing import List, Dict, Optional
import logging


class DetailLoader:
    """Load table relationships, measures, columns, and Power Query from database."""
    
    @staticmethod
    def load_relationships(table_name: Optional[str] = None, workspace_filter: Optional[str] = None, 
                          dataset_filter: Optional[str] = None, source_filter: Optional[str] = None,
                          table_search: Optional[str] = None, relationship_type: Optional[str] = None) -> List[Dict]:
        """Load relationships from database, optionally filtered by table name and other filters."""
        try:
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # Build WHERE clause for filters
            where_conditions = []
            params = []
            
            if table_name:
                # Get object_id for the table
                cursor.execute('SELECT object_id FROM data_objects WHERE object_name = ?', (table_name,))
                obj = cursor.fetchone()
                if not obj:
                    logging.warning(f"Table {table_name} not found in database")
                    db.conn.close()
                    return []
                object_id = obj[0]
                where_conditions.append('(r.from_object_id = ? OR r.to_object_id = ?)')
                params.extend([object_id, object_id])
            
            # Add workspace filter
            if workspace_filter and workspace_filter != 'All Workspaces':
                where_conditions.append('w.workspace_name = ?')
                params.append(workspace_filter)
            
            # Add dataset filter
            if dataset_filter and dataset_filter != 'All Datasets':
                where_conditions.append('ds.dataset_name = ?')
                params.append(dataset_filter)
            
            # Add source filter
            if source_filter and source_filter != 'All Sources':
                where_conditions.append('ds.source_type = ?')
                params.append(source_filter)
            
            # Add table search filter (searches in from_table and to_table)
            if table_search:
                where_conditions.append('(do_from.object_name LIKE ? OR do_to.object_name LIKE ?)')
                params.append(f'%{table_search}%')
                params.append(f'%{table_search}%')
            
            # Add relationship type filter
            if relationship_type and relationship_type != 'All':
                where_conditions.append('r.cardinality = ?')
                params.append(relationship_type)
            
            # Build query
            query = '''
                SELECT 
                    w.workspace_name,
                    ds.dataset_name,
                    do_from.object_name as from_table,
                    r.from_column,
                    do_to.object_name as to_table,
                    r.to_column,
                    r.cardinality,
                    r.is_active
                FROM relationships r
                JOIN data_objects do_from ON r.from_object_id = do_from.object_id
                JOIN data_objects do_to ON r.to_object_id = do_to.object_id
                JOIN datasets ds ON do_from.dataset_id = ds.dataset_id
                JOIN workspaces w ON ds.workspace_id = w.workspace_id
            '''
            
            if where_conditions:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            db.conn.close()
            
            results = []
            for row in rows:
                results.append({
                    'workspace': row[0],
                    'dataset': row[1],
                    'from_table': row[2],
                    'from_column': row[3],
                    'to_table': row[4],
                    'to_column': row[5],
                    'cardinality': row[6] or 'many-to-one',
                    'is_active': row[7]
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Error loading relationships from database: {e}", exc_info=True)
            return []
    
    @staticmethod
    def load_measures(table_name: Optional[str] = None, workspace_filter: Optional[str] = None,
                     dataset_filter: Optional[str] = None, source_filter: Optional[str] = None,
                     table_search: Optional[str] = None) -> List[Dict]:
        """Load measures from database, optionally filtered by table name and other filters."""
        try:
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # Build WHERE clause for filters
            where_conditions = []
            params = []
            
            if table_name:
                # Get object_id for the table
                cursor.execute('SELECT object_id FROM data_objects WHERE object_name = ?', (table_name,))
                obj = cursor.fetchone()
                if not obj:
                    logging.warning(f"Table {table_name} not found in database")
                    db.conn.close()
                    return []
                object_id = obj[0]
                where_conditions.append('m.object_id = ?')
                params.append(object_id)
            
            # Add workspace filter
            if workspace_filter and workspace_filter != 'All Workspaces':
                where_conditions.append('w.workspace_name = ?')
                params.append(workspace_filter)
            
            # Add dataset filter
            if dataset_filter and dataset_filter != 'All Datasets':
                where_conditions.append('ds.dataset_name = ?')
                params.append(dataset_filter)
            
            # Add source filter
            if source_filter and source_filter != 'All Sources':
                where_conditions.append('ds.source_type = ?')
                params.append(source_filter)
            
            # Add table search filter
            if table_search:
                where_conditions.append('do.object_name LIKE ?')
                params.append(f'%{table_search}%')
            
            # Build query
            query = '''
                SELECT w.workspace_name, ds.dataset_name, m.measure_name, m.expression, m.format_string, m.is_hidden
                FROM measures m
                JOIN data_objects do ON m.object_id = do.object_id
                JOIN datasets ds ON do.dataset_id = ds.dataset_id
                JOIN workspaces w ON ds.workspace_id = w.workspace_id
            '''
            
            if where_conditions:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            db.conn.close()
            
            results = []
            for row in rows:
                results.append({
                    'workspace': row[0],
                    'dataset': row[1],
                    'measure_name': row[2],
                    'expression': row[3],
                    'format_string': row[4] or '',
                    'is_hidden': row[5]
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Error loading measures from database: {e}", exc_info=True)
            return []
    
    @staticmethod
    def load_columns(table_name: Optional[str] = None, workspace_filter: Optional[str] = None,
                    dataset_filter: Optional[str] = None, source_filter: Optional[str] = None,
                    table_search: Optional[str] = None) -> List[Dict]:
        """Load columns from database, optionally filtered by table name and other filters."""
        try:
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # Build WHERE clause for filters
            where_conditions = []
            params = []
            
            if table_name:
                # Get object_id for the table
                cursor.execute('SELECT object_id FROM data_objects WHERE object_name = ?', (table_name,))
                obj = cursor.fetchone()
                if not obj:
                    logging.warning(f"Table {table_name} not found in database")
                    db.conn.close()
                    return []
                object_id = obj[0]
                where_conditions.append('tc.object_id = ?')
                params.append(object_id)
            
            # Add workspace filter
            if workspace_filter and workspace_filter != 'All Workspaces':
                where_conditions.append('w.workspace_name = ?')
                params.append(workspace_filter)
            
            # Add dataset filter
            if dataset_filter and dataset_filter != 'All Datasets':
                where_conditions.append('ds.dataset_name = ?')
                params.append(dataset_filter)
            
            # Add source filter
            if source_filter and source_filter != 'All Sources':
                where_conditions.append('ds.source_type = ?')
                params.append(source_filter)
            
            # Add table search filter
            if table_search:
                where_conditions.append('do.object_name LIKE ?')
                params.append(f'%{table_search}%')
            
            # Build query - always include workspace, dataset, and table name
            query = '''
                SELECT w.workspace_name, ds.dataset_name, do.object_name, tc.column_name, tc.data_type, tc.format_string, tc.source_column, tc.is_hidden
                FROM columns tc
                JOIN data_objects do ON tc.object_id = do.object_id
                JOIN datasets ds ON do.dataset_id = ds.dataset_id
                JOIN workspaces w ON ds.workspace_id = w.workspace_id
            '''
            
            if where_conditions:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            db.conn.close()
            
            results = []
            for row in rows:
                results.append({
                    'workspace': row[0],
                    'dataset': row[1],
                    'table_name': row[2],
                    'column_name': row[3],
                    'data_type': row[4] or '-',
                    'format_string': row[5] or '-',
                    'source_column': row[6] or '-',
                    'is_hidden': row[7]
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Error loading columns from database: {e}", exc_info=True)
            return []
    
    @staticmethod
    def load_power_query(table_name: str) -> Optional[str]:
        """Load Power Query M code from database for a specific table."""
        try:
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # Get object_id for the table
            cursor.execute('SELECT object_id FROM data_objects WHERE object_name = ?', (table_name,))
            obj = cursor.fetchone()
            if not obj:
                logging.warning(f"Table {table_name} not found in database")
                db.conn.close()
                return None
            object_id = obj[0]
            
            # Get Power Query M code
            cursor.execute('SELECT m_code FROM power_query WHERE object_id = ?', (object_id,))
            row = cursor.fetchone()
            db.conn.close()
            
            return row[0] if row else None
            
        except Exception as e:
            logging.error(f"Error loading Power Query from database: {e}", exc_info=True)
            return None
