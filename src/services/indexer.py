"""Indexing service for scanning and importing BI tool metadata."""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from database.schema import FabricDatabase
from parsers import BaseParser, PowerBIParser
from models import Workspace, Dataset, DataObject, DataSource


class IndexingService:
    """Service for indexing BI tool metadata into database."""
    
    def __init__(self, db: FabricDatabase):
        """
        Initialize indexing service.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.parsers = {
            'powerbi': PowerBIParser(),
            # 'tableau': TableauParser(),  # Future
        }
    
    def _register_tool(self, tool_id: str):
        """Register or update BI tool in database."""
        cursor = self.db.conn.cursor()
        
        tool_info = {
            'powerbi': ('Power BI', 'Power BI Desktop & Service'),
            'tableau': ('Tableau', 'Tableau Desktop & Server'),
        }
        
        tool_name, description = tool_info.get(tool_id, (tool_id, f'{tool_id} tool'))
        
        # Insert or ignore if already exists
        cursor.execute('''
            INSERT OR IGNORE INTO bi_tools (tool_id, tool_name, description)
            VALUES (?, ?, ?)
        ''', (tool_id, tool_name, description))
        
        self.db.conn.commit()
        
    def index_export_folder(self, export_path: Path, tool_id: str = 'powerbi', 
                           parallel: bool = True, max_workers: int = 10) -> dict:
        """
        Index an entire export folder.
        
        Args:
            export_path: Path to export folder
            tool_id: BI tool identifier ('powerbi', 'tableau', etc.)
            parallel: Use parallel processing
            max_workers: Maximum parallel workers
            
        Returns:
            Dictionary with indexing statistics
        """
        parser = self.parsers.get(tool_id)
        if not parser:
            raise ValueError(f"No parser available for tool: {tool_id}")
        
        # Ensure tool is registered in database
        self._register_tool(tool_id)
            
        stats = {
            'workspaces': 0,
            'datasets': 0,
            'data_objects': 0,
            'data_sources': 0,
            'relationships': 0,
            'measures': 0,
            'columns': 0,
            'power_queries': 0,
            'errors': []
        }
        
        # Find workspace folders - check for both Raw Files and Processed_Data
        if (export_path / "Raw Files").exists():
            workspace_root = export_path / "Raw Files"
        elif export_path.name == "Processed_Data":
            # If path ends with Processed_Data, use it directly
            workspace_root = export_path
        elif (export_path / "Processed_Data").exists():
            workspace_root = export_path / "Processed_Data"
        else:
            workspace_root = export_path
            
        workspace_folders = [f for f in workspace_root.iterdir() if f.is_dir()]
        
        if parallel:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._index_workspace, folder, parser): folder 
                    for folder in workspace_folders
                }
                
                for future in as_completed(futures):
                    try:
                        ws_stats = future.result()
                        for key in stats:
                            if key != 'errors' and key in ws_stats:
                                stats[key] += ws_stats[key]
                        if ws_stats.get('errors'):
                            stats['errors'].extend(ws_stats['errors'])
                    except Exception as e:
                        folder = futures[future]
                        stats['errors'].append(f"Error indexing {folder.name}: {str(e)}")
        else:
            for folder in workspace_folders:
                try:
                    ws_stats = self._index_workspace(folder, parser)
                    for key in stats:
                        if key != 'errors' and key in ws_stats:
                            stats[key] += ws_stats[key]
                    if ws_stats.get('errors'):
                        stats['errors'].extend(ws_stats['errors'])
                except Exception as e:
                    stats['errors'].append(f"Error indexing {folder.name}: {str(e)}")
                    
        return stats
        
    def _index_workspace(self, workspace_folder: Path, parser: BaseParser) -> dict:
        """Index a single workspace."""
        stats = {
            'workspaces': 0,
            'datasets': 0,
            'data_objects': 0,
            'data_sources': 0,
            'relationships': 0,
            'measures': 0,
            'columns': 0,
            'power_queries': 0,
            'errors': []
        }
        
        try:
            # Parse workspace
            workspace = parser.parse_workspace(workspace_folder)
            workspace.save(self.db.conn)
            stats['workspaces'] += 1
            
            # Find semantic models/datasets
            for item_folder in workspace_folder.glob("*.SemanticModel"):
                try:
                    dataset_stats = self._index_dataset(item_folder, workspace.workspace_id, parser)
                    for key in stats:
                        if key != 'errors' and key in dataset_stats:
                            stats[key] += dataset_stats[key]
                    if dataset_stats.get('errors'):
                        stats['errors'].extend(dataset_stats['errors'])
                except Exception as e:
                    stats['errors'].append(f"Error indexing dataset {item_folder.name}: {str(e)}")
                    
        except Exception as e:
            stats['errors'].append(f"Error indexing workspace {workspace_folder.name}: {str(e)}")
            
        return stats
        
    def _index_dataset(self, dataset_path: Path, workspace_id: str, parser: BaseParser) -> dict:
        """Index a single dataset."""
        stats = {
            'datasets': 0,
            'data_objects': 0,
            'data_sources': 0,
            'relationships': 0,
            'measures': 0,
            'columns': 0,
            'power_queries': 0,
            'errors': []
        }
        
        try:
            # Parse dataset
            dataset = parser.parse_dataset(dataset_path, workspace_id)
            dataset.save(self.db.conn)
            stats['datasets'] += 1
            
            # Parse data objects (tables) FIRST - must exist before relationships/measures
            data_objects = parser.parse_data_objects(dataset_path, dataset.dataset_id)
            
            for data_object in data_objects:
                try:
                    # Save data object
                    object_id = data_object.save(self.db.conn)
                    stats['data_objects'] += 1
                    
                    # Parse and save columns for this table
                    try:
                        table_path = dataset_path / "definition" / "tables" / f"{data_object.object_name}.tmdl"
                        if table_path.exists():
                            columns = parser.parse_columns(table_path, data_object.object_name)
                            cursor = self.db.conn.cursor()
                            for col in columns:
                                try:
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO columns 
                                        (object_id, column_name, data_type, format_string, source_column, expression, is_hidden)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', (object_id, col['column_name'], col.get('data_type', ''), 
                                          col.get('format_string', ''), col.get('source_column', ''),
                                          col.get('expression', ''), col.get('is_hidden', False)))
                                    stats['columns'] += 1
                                except Exception as e:
                                    stats['errors'].append(f"Error saving column {col['column_name']}: {str(e)}")
                            self.db.conn.commit()
                            
                            # Parse and save Power Query M code
                            try:
                                m_code = parser.parse_partition(table_path)
                                if m_code:
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO power_query (object_id, m_code)
                                        VALUES (?, ?)
                                    ''', (object_id, m_code))
                                    stats['power_queries'] += 1
                                    self.db.conn.commit()
                            except Exception as e:
                                stats['errors'].append(f"Error saving Power Query for {data_object.object_name}: {str(e)}")
                    except Exception as e:
                        stats['errors'].append(f"Error parsing columns/Power Query for {data_object.object_name}: {str(e)}")
                    
                    # Parse data sources for this object
                    if table_path.exists():
                        data_sources = parser.parse_data_sources(table_path, object_id)
                        
                        for data_source in data_sources:
                            try:
                                data_source.dataset_id = dataset.dataset_id
                                data_source.save(self.db.conn)
                                stats['data_sources'] += 1
                            except Exception as e:
                                stats['errors'].append(
                                    f"Error saving data source in {data_object.object_name}: {str(e)}"
                                )
                                
                except Exception as e:
                    stats['errors'].append(f"Error indexing data object {data_object.object_name}: {str(e)}")
            
            # NOW parse and save relationships (after all tables exist)
            try:
                relationships = parser.parse_relationships(dataset_path, dataset.dataset_id)
                cursor = self.db.conn.cursor()
                for rel in relationships:
                    try:
                        # Get object_ids for from/to tables
                        cursor.execute('SELECT object_id FROM data_objects WHERE dataset_id = ? AND object_name = ?',
                                     (dataset.dataset_id, rel['from_table']))
                        from_obj = cursor.fetchone()
                        cursor.execute('SELECT object_id FROM data_objects WHERE dataset_id = ? AND object_name = ?',
                                     (dataset.dataset_id, rel['to_table']))
                        to_obj = cursor.fetchone()
                        
                        if from_obj and to_obj:
                            cursor.execute('''
                                INSERT OR REPLACE INTO relationships 
                                (dataset_id, from_object_id, from_column, to_object_id, to_column, cardinality, is_active)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (dataset.dataset_id, from_obj[0], rel['from_column'], 
                                  to_obj[0], rel['to_column'], rel.get('cardinality', 'many-to-one'), 
                                  rel.get('is_active', True)))
                            stats['relationships'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Error saving relationship: {str(e)}")
                self.db.conn.commit()
            except Exception as e:
                stats['errors'].append(f"Error parsing relationships: {str(e)}")
            
            # Parse and save measures (after all tables exist)
            try:
                measures = parser.parse_measures(dataset_path, "")
                cursor = self.db.conn.cursor()
                for measure in measures:
                    try:
                        # Get object_id for table
                        cursor.execute('SELECT object_id FROM data_objects WHERE dataset_id = ? AND object_name = ?',
                                     (dataset.dataset_id, measure['table_name']))
                        obj = cursor.fetchone()
                        
                        if obj:
                            cursor.execute('''
                                INSERT OR REPLACE INTO measures 
                                (dataset_id, object_id, measure_name, expression, format_string, is_hidden)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (dataset.dataset_id, obj[0], measure['measure_name'], 
                                  measure['expression'], measure.get('format_string', ''), 
                                  measure.get('is_hidden', False)))
                            stats['measures'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Error saving measure {measure['measure_name']}: {str(e)}")
                self.db.conn.commit()
            except Exception as e:
                stats['errors'].append(f"Error parsing measures: {str(e)}")
            
            # Parse data objects (tables)
            data_objects = parser.parse_data_objects(dataset_path, dataset.dataset_id)
            
            for data_object in data_objects:
                try:
                    # Save data object
                    object_id = data_object.save(self.db.conn)
                    stats['data_objects'] += 1
                    
                    # Parse and save columns for this table
                    try:
                        table_path = dataset_path / "definition" / "tables" / f"{data_object.object_name}.tmdl"
                        if table_path.exists():
                            columns = parser.parse_columns(table_path, data_object.object_name)
                            cursor = self.db.conn.cursor()
                            for col in columns:
                                try:
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO columns 
                                        (object_id, column_name, data_type, format_string, source_column, expression, is_hidden)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', (object_id, col['column_name'], col.get('data_type', ''), 
                                          col.get('format_string', ''), col.get('source_column', ''),
                                          col.get('expression', ''), col.get('is_hidden', False)))
                                    stats['columns'] += 1
                                except Exception as e:
                                    stats['errors'].append(f"Error saving column {col['column_name']}: {str(e)}")
                            self.db.conn.commit()
                            
                            # Parse and save Power Query M code
                            try:
                                m_code = parser.parse_partition(table_path)
                                if m_code:
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO power_query (object_id, m_code)
                                        VALUES (?, ?)
                                    ''', (object_id, m_code))
                                    stats['power_queries'] += 1
                                    self.db.conn.commit()
                            except Exception as e:
                                stats['errors'].append(f"Error saving Power Query for {data_object.object_name}: {str(e)}")
                    except Exception as e:
                        stats['errors'].append(f"Error parsing columns/Power Query for {data_object.object_name}: {str(e)}")
                    
                    # Parse data sources for this object
                    table_path = dataset_path / "definition" / "tables" / f"{data_object.object_name}.tmdl"
                    if table_path.exists():
                        data_sources = parser.parse_data_sources(table_path, object_id)
                        
                        for data_source in data_sources:
                            try:
                                data_source.dataset_id = dataset.dataset_id
                                data_source.save(self.db.conn)
                                stats['data_sources'] += 1
                            except Exception as e:
                                stats['errors'].append(
                                    f"Error saving data source in {data_object.object_name}: {str(e)}"
                                )
                                
                except Exception as e:
                    stats['errors'].append(f"Error indexing data object {data_object.object_name}: {str(e)}")
                    
        except Exception as e:
            stats['errors'].append(f"Error indexing dataset {dataset_path.name}: {str(e)}")
            
        return stats
        
    def re_index_workspace(self, workspace_id: str, export_path: Path) -> dict:
        """Re-index a specific workspace."""
        # Delete existing data
        cursor = self.db.conn.cursor()
        cursor.execute('DELETE FROM workspaces WHERE workspace_id = ?', (workspace_id,))
        self.db.conn.commit()
        
        # Re-index
        workspace = Workspace.get_by_id(self.db.conn, workspace_id)
        if workspace:
            workspace_path = Path(workspace.description)  # Assuming path stored in description
            parser = self.parsers.get(workspace.tool_id)
            return self._index_workspace(workspace_path, parser)
        
        return {'error': 'Workspace not found'}
        
    def clear_and_reindex(self, export_path: Path, tool_id: str = 'powerbi') -> dict:
        """Clear database and re-index from scratch."""
        # Clear all data
        self.db.clear_all_data(confirm=True)
        
        # Re-index
        return self.index_export_folder(export_path, tool_id)
        
    def get_indexing_status(self) -> dict:
        """Get current indexing status and statistics."""
        return self.db.get_stats()
