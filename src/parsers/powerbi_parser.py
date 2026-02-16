"""Power BI TMDL parser implementation."""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .base_parser import BaseParser
from models import Workspace, Dataset, DataObject, DataSource


class PowerBIParser(BaseParser):
    """Parser for Power BI TMDL (Tabular Model Definition Language) format."""
    
    def __init__(self):
        super().__init__(tool_id='powerbi')
        
    def parse_workspace(self, path: Path) -> Workspace:
        """Parse Power BI workspace from export path."""
        workspace_name = path.name
        workspace_id = f"powerbi_{workspace_name}_{path.stat().st_mtime}"
        
        # Count items in workspace
        item_count = len(list(path.glob("*.SemanticModel"))) + len(list(path.glob("*.Report")))
        
        return Workspace(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            tool_id=self.tool_id,
            workspace_type='Fabric Workspace',
            description=f'Power BI workspace with {item_count} items',
            last_scanned=datetime.now(),
            scan_status='completed'
        )
        
    def parse_dataset(self, path: Path, workspace_id: str) -> Dataset:
        """Parse Power BI semantic model from TMDL."""
        dataset_name = path.name.replace('.SemanticModel', '')
        dataset_id = f"{workspace_id}_{dataset_name}"
        
        # Read database.tmdl for model properties
        database_file = path / "definition" / "database.tmdl"
        model_file = path / "definition" / "model.tmdl"
        
        model_properties = {}
        compatibility_level = None
        
        if database_file.exists():
            content = database_file.read_text(encoding='utf-8-sig', errors='ignore')
            
            # Extract compatibility level
            compat_match = re.search(r'compatibilityLevel:\s*(\d+)', content)
            if compat_match:
                compatibility_level = int(compat_match.group(1))
                
        if model_file.exists():
            content = model_file.read_text(encoding='utf-8-sig', errors='ignore')
            
            # Extract model properties
            mode_match = re.search(r'defaultMode:\s*(\w+)', content)
            if mode_match:
                model_properties['defaultMode'] = mode_match.group(1)
                
        # Get file size
        size_bytes = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        
        return Dataset(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            workspace_id=workspace_id,
            tool_id=self.tool_id,
            dataset_type='Semantic Model',
            file_path=str(path),
            compatibility_level=compatibility_level,
            model_type='Import',  # Default, can be enhanced
            data_access_mode=model_properties.get('defaultMode', 'import'),
            tool_specific_metadata=model_properties,
            last_analyzed=datetime.now(),
            size_bytes=size_bytes
        )
        
    def parse_data_objects(self, dataset_path: Path, dataset_id: str) -> List[DataObject]:
        """Parse tables from TMDL files."""
        data_objects = []
        
        tables_path = dataset_path / "definition" / "tables"
        if not tables_path.exists():
            return data_objects
            
        # Sort files to ensure consistent object_id assignment across indexing runs
        for table_file in sorted(tables_path.glob("*.tmdl")):
            table_name = table_file.stem
            content = table_file.read_text(encoding='utf-8-sig', errors='ignore')
            
            # Count columns
            column_count = content.count('column ')
            
            # Count partitions
            partition_count = content.count('partition ')
            has_partitions = partition_count > 0
            
            # Check if hidden
            is_hidden = 'isHidden' in content or 'isHidden: true' in content
            
            # Extract table properties
            metadata = {
                'lineageTag': self._extract_property(content, 'lineageTag'),
                'sourceLineageTag': self._extract_property(content, 'sourceLineageTag'),
            }
            
            data_object = DataObject(
                object_id=None,  # Will be set when saved
                dataset_id=dataset_id,
                object_name=table_name,
                object_type='Table',
                partition_count=partition_count,
                column_count=column_count,
                has_partitions=has_partitions,
                is_hidden=is_hidden,
                tool_specific_metadata=metadata
            )
            
            data_objects.append(data_object)
            
        return data_objects
        
    def parse_data_sources(self, data_object_path: Path, object_id: int) -> List[DataSource]:
        """Parse data sources from table TMDL file."""
        data_sources = []
        
        if not data_object_path.exists():
            return data_sources
            
        content = data_object_path.read_text(encoding='utf-8-sig', errors='ignore')
        
        # Extract SQL Server sources
        sql_sources = self._extract_sql_sources(content)
        for source in sql_sources:
            source.object_id = object_id
            source.requires_migration = self.detect_migration_needs(source)
            data_sources.append(source)
            
        # Extract Excel sources
        excel_sources = self._extract_excel_sources(content)
        for source in excel_sources:
            source.object_id = object_id
            source.requires_migration = self.detect_migration_needs(source)
            data_sources.append(source)
            
        # Extract CSV sources
        csv_sources = self._extract_csv_sources(content)
        for source in csv_sources:
            source.object_id = object_id
            source.requires_migration = self.detect_migration_needs(source)
            data_sources.append(source)
            
        # Extract Web sources
        web_sources = self._extract_web_sources(content)
        for source in web_sources:
            source.object_id = object_id
            source.requires_migration = self.detect_migration_needs(source)
            data_sources.append(source)
            
        # Extract SharePoint sources
        sharepoint_sources = self._extract_sharepoint_sources(content)
        for source in sharepoint_sources:
            source.object_id = object_id
            source.requires_migration = self.detect_migration_needs(source)
            data_sources.append(source)
            
        # Extract M expression (Power Query)
        m_expressions = self._extract_m_expressions(content)
        for source in m_expressions:
            source.object_id = object_id
            source.requires_migration = self.detect_migration_needs(source)
            data_sources.append(source)
            
        return data_sources
        
    def _extract_sql_sources(self, content: str) -> List[DataSource]:
        """Extract SQL Server data sources."""
        sources = []
        
        # Pattern 1: Sql.Database("server", "database") - older format
        sql_pattern1 = r'Sql\.Database\("([^"]+)"(?:,\s*"([^"]+)")?\)'
        
        for match in re.finditer(sql_pattern1, content):
            server = match.group(1)
            database = match.group(2) if match.group(2) else ''
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='SQL Server',
                source_name=f"{server}/{database}" if database else server,
                server=server,
                database_name=database,
                connection_string=f"Server={server};Database={database}",
                migration_priority=1
            )
            sources.append(source)
        
        # Pattern 2: Sql.Databases("server") - newer format
        # Then database name is extracted from: Source{[Name="database"]}[Data]
        sql_pattern2 = r'Sql\.Databases\("([^"]+)"\)'
        
        for match in re.finditer(sql_pattern2, content):
            server = match.group(1)
            
            # Try to find database name in the following lines
            # Pattern: Source{[Name="database"]}[Data] or variable = Source{[Name="database"]}[Data]
            db_pattern = r'\{[^}]*Name\s*=\s*"([^"]+)"[^}]*\}\[Data\]'
            db_matches = list(re.finditer(db_pattern, content))
            
            if db_matches:
                # Use first database name found (typically right after Sql.Databases)
                database = db_matches[0].group(1)
            else:
                database = ''
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='SQL Server',
                source_name=f"{server}/{database}" if database else server,
                server=server,
                database_name=database,
                connection_string=f"Server={server};Database={database}",
                migration_priority=1
            )
            sources.append(source)
            
        return sources
        
    def _extract_excel_sources(self, content: str) -> List[DataSource]:
        """Extract Excel data sources."""
        sources = []
        
        # Pattern 1: Excel.Workbook(File.Contents("literal_path")) - hardcoded path
        excel_pattern1 = r'Excel\.Workbook\(.*?File\.Contents\("([^"]+)"\)'
        
        for match in re.finditer(excel_pattern1, content):
            file_path = match.group(1)
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='Excel',
                source_name=Path(file_path).name,
                connection_string=file_path,
                tool_specific_metadata={'file_path': file_path},
                migration_priority=2
            )
            sources.append(source)
        
        # Pattern 2: Excel.Workbook(File.Contents(ParameterName)) - parameter reference
        excel_pattern2 = r'Excel\.Workbook\(File\.Contents\((\w+)\)'
        
        for match in re.finditer(excel_pattern2, content):
            parameter_name = match.group(1)
            
            # Create source with parameter name
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='Excel',
                source_name=f"Excel (Parameter: {parameter_name})",
                connection_string=f"Parameter:{parameter_name}",
                server=parameter_name,  # Store parameter name in server field
                tool_specific_metadata={'parameter': parameter_name},
                migration_priority=2
            )
            sources.append(source)
        
        return sources
        
    def _extract_csv_sources(self, content: str) -> List[DataSource]:
        """Extract CSV data sources."""
        sources = []
        
        # Pattern 1: Csv.Document(File.Contents("literal_path")) - hardcoded path
        csv_pattern1 = r'Csv\.Document\(File\.Contents\("([^"]+)"\)'
        
        for match in re.finditer(csv_pattern1, content):
            file_path = match.group(1)
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='CSV',
                source_name=Path(file_path).name,
                connection_string=file_path,
                tool_specific_metadata={'file_path': file_path},
                migration_priority=2
            )
            sources.append(source)
        
        # Pattern 2: Csv.Document(File.Contents(ParameterName)) - parameter reference
        csv_pattern2 = r'Csv\.Document\(File\.Contents\((\w+)\)'
        
        for match in re.finditer(csv_pattern2, content):
            parameter_name = match.group(1)
            
            # Create source with parameter name
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='CSV',
                source_name=f"CSV (Parameter: {parameter_name})",
                connection_string=f"Parameter:{parameter_name}",
                server=parameter_name,  # Store parameter name in server field
                tool_specific_metadata={'parameter': parameter_name},
                migration_priority=2
            )
            sources.append(source)
        
        return sources
        
    def _extract_web_sources(self, content: str) -> List[DataSource]:
        """Extract Web data sources."""
        sources = []
        
        # Pattern: Web.Contents("url")
        web_pattern = r'Web\.Contents\("([^"]+)"\)'
        
        for match in re.finditer(web_pattern, content):
            url = match.group(1)
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type='Web',
                source_name=url,
                server=url,
                connection_string=url,
                migration_priority=3
            )
            sources.append(source)
            
        return sources
        
    def _extract_sharepoint_sources(self, content: str) -> List[DataSource]:
        """Extract SharePoint data sources."""
        sources = []
        
        # Pattern: SharePoint.Files("url") or SharePoint.Contents("url")
        sp_pattern = r'SharePoint\.(Files|Contents)\("([^"]+)"\)'
        
        for match in re.finditer(sp_pattern, content):
            sp_type = match.group(1)
            url = match.group(2)
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type=f'SharePoint {sp_type}',
                source_name=url,
                server=url,
                connection_string=url,
                tool_specific_metadata={'sharepoint_type': sp_type},
                migration_priority=2
            )
            sources.append(source)
            
        return sources
        
    def _extract_m_expressions(self, content: str) -> List[DataSource]:
        """Extract M (Power Query) expressions."""
        sources = []
        
        # Extract partition with M source
        partition_pattern = r'partition\s+([^\s=]+)\s*=\s*m\s*\n\s*expression:\s*```\s*(.+?)```'
        
        for match in re.finditer(partition_pattern, content, re.DOTALL):
            partition_name = match.group(1).strip("'\"")
            m_expression = match.group(2).strip()
            
            # Determine source type from M expression
            source_type = self._determine_source_type_from_m(m_expression)
            
            source = DataSource(
                source_id=None,
                object_id=None,
                dataset_id=None,
                source_type=source_type,
                source_name=partition_name,
                m_expression=m_expression,
                query=m_expression[:500],  # Store first 500 chars
                tool_specific_metadata={'partition_name': partition_name, 'full_expression': m_expression},
                migration_priority=1 if 'Sql.Database' in m_expression else 3
            )
            sources.append(source)
            
        return sources
        
    def _determine_source_type_from_m(self, m_expression: str) -> str:
        """Determine data source type from M expression."""
        if 'Sql.Database' in m_expression or 'Sql.Databases' in m_expression:
            return 'SQL Server'
        elif 'Oracle.Database' in m_expression:
            return 'Oracle'
        elif 'PostgreSQL.Database' in m_expression:
            return 'PostgreSQL'
        elif 'MySql.Database' in m_expression:
            return 'MySQL'
        elif 'Excel.Workbook' in m_expression:
            return 'Excel'
        elif 'Csv.Document' in m_expression:
            return 'CSV'
        elif 'File.Contents' in m_expression:
            return 'File'
        elif 'Web.Contents' in m_expression or 'Web.Page' in m_expression:
            return 'Web'
        elif 'SharePoint' in m_expression:
            return 'SharePoint'
        elif 'OData.Feed' in m_expression:
            return 'OData'
        elif 'Json.Document' in m_expression:
            return 'JSON'
        else:
            return 'Power Query'
            
    def detect_migration_needs(self, data_source: DataSource) -> bool:
        """Determine if data source requires migration."""
        # SQL sources that reference on-premise servers
        if data_source.source_type == 'SQL Server':
            if data_source.server:
                # Local server indicators
                if any(keyword in data_source.server.lower() for keyword in ['localhost', '127.0.0.1', '.\\', '(local)']):
                    return True
                # Non-Azure SQL servers (simple heuristic)
                if 'database.windows.net' not in data_source.server.lower():
                    return True
                    
        # Excel/CSV/File sources need migration
        elif data_source.source_type in ['Excel', 'CSV', 'File']:
            return True
            
        # SharePoint sources may need migration
        elif 'SharePoint' in data_source.source_type:
            return True
            
        # Web sources may need review
        elif data_source.source_type == 'Web':
            return False  # Usually OK
            
        return False
        
    def _extract_property(self, content: str, property_name: str) -> Optional[str]:
        """Extract a property value from TMDL content."""
        pattern = rf'{property_name}:\s*(.+?)(?:\n|\r)'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip().strip('"\'')
        return None
        
    def parse_relationships(self, dataset_path: Path, dataset_id: str) -> List[Dict]:
        """Parse relationships from TMDL relationships file."""
        relationships = []
        
        relationships_file = dataset_path / "definition" / "relationships.tmdl"
        if not relationships_file.exists():
            return relationships
            
        content = relationships_file.read_text(encoding='utf-8-sig', errors='ignore')
        
        # Parse relationship blocks - format uses tabs, not spaces
        # relationship <guid>\n\tfromColumn: Table.Column\n\ttoColumn: Table.Column
        relationship_blocks = re.split(r'\nrelationship\s+', content)
        
        for block in relationship_blocks[1:]:  # Skip first empty block
            lines = block.split('\n')
            rel_id = lines[0].strip()
            
            from_table = None
            from_column = None
            to_table = None
            to_column = None
            is_active = True
            cross_filter = 'single'
            
            # Parse properties (with tabs)
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('fromColumn:'):
                    # Format: fromColumn: TableName.ColumnName or fromColumn: TableName.'Column Name'
                    col_ref = line.split(':', 1)[1].strip()
                    if '.' in col_ref:
                        parts = col_ref.split('.', 1)
                        from_table = parts[0].strip().strip("'\"")
                        from_column = parts[1].strip().strip("'\"")
                elif line.startswith('toColumn:'):
                    col_ref = line.split(':', 1)[1].strip()
                    if '.' in col_ref:
                        parts = col_ref.split('.', 1)
                        to_table = parts[0].strip().strip("'\"")
                        to_column = parts[1].strip().strip("'\"")
                elif line.startswith('isActive:'):
                    is_active = 'false' not in line.lower()
                elif line.startswith('crossFilterDirection:'):
                    cross_filter = 'both' if 'both' in line.lower() else 'single'
            
            if from_table and to_table:
                relationships.append({
                    'relationship_id': rel_id,
                    'dataset_id': dataset_id,
                    'from_table': from_table,
                    'from_column': from_column,
                    'to_table': to_table,
                    'to_column': to_column,
                    'cardinality': 'many-to-one',
                    'cross_filter_direction': cross_filter,
                    'is_active': is_active
                })
        
        return relationships
    
    def parse_measures(self, dataset_path: Path, dataset_id: str) -> List[Dict]:
        """Parse measures from TMDL table files."""
        measures = []
        
        tables_path = dataset_path / "definition" / "tables"
        if not tables_path.exists():
            return measures
            
        for table_file in tables_path.glob("*.tmdl"):
            table_name = table_file.stem
            content = table_file.read_text(encoding='utf-8-sig', errors='ignore')
            
            # Parse measure blocks - handle quoted names
            # Format: measure MeasureName = <expression> or measure 'Measure Name' = <expression>
            
            # Split by measure keyword
            measure_blocks = re.split(r'\n\s+measure\s+', content)
            
            for block in measure_blocks[1:]:  # Skip first block
                lines = block.split('\n')
                first_line = lines[0]
                
                # Extract measure name and start of expression
                # Format: 'Measure Name' = expression OR MeasureName = expression
                if '=' in first_line:
                    parts = first_line.split('=', 1)
                    measure_name = parts[0].strip().strip("'\"")
                    expression_start = parts[1].strip()
                else:
                    continue
                
                # Collect full expression (may span multiple lines)
                expression_lines = [expression_start]
                is_hidden = False
                format_string = None
                
                for line in lines[1:]:
                    stripped = line.strip()
                    # Stop at next property or block
                    if stripped.startswith(('lineageTag:', 'column ', 'measure ', 'partition ', 'annotation ')):
                        break
                    elif stripped.startswith('formatString:'):
                        format_string = stripped.split(':', 1)[1].strip().strip('"\'')
                    elif stripped.startswith('isHidden'):
                        is_hidden = True
                    else:
                        # Part of the expression
                        if stripped and not stripped.startswith(('displayFolder:', 'description:')):
                            expression_lines.append(line.strip())
                
                expression = ' '.join(expression_lines).strip()
                
                measures.append({
                    'dataset_id': dataset_id,
                    'table_name': table_name,
                    'measure_name': measure_name,
                    'expression': expression,
                    'format_string': format_string,
                    'is_hidden': is_hidden
                })
        
        return measures
    
    def parse_columns(self, table_file: Path, table_name: str) -> List[Dict]:
        """Parse columns from a table TMDL file."""
        columns = []
        
        if not table_file.exists():
            return columns
            
        content = table_file.read_text(encoding='utf-8-sig', errors='ignore')
        
        # Parse column blocks - handle both simple and quoted names
        # Format: column ColumnName\n\t\tdataType: type\n\t\t...
        # or: column 'Column Name'\n\t\tdataType: type\n\t\t...
        
        # Split by column keyword
        column_blocks = re.split(r'\n\s+column\s+', content)
        
        for block in column_blocks[1:]:  # Skip first block (before first column)
            lines = block.split('\n')
            
            # First line is the column name
            column_name = lines[0].strip().strip("'\"")
            
            # Parse properties
            data_type = 'string'
            is_hidden = False
            format_string = None
            source_column = None
            expression = None
            
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('dataType:'):
                    data_type = line.split(':', 1)[1].strip()
                elif line.startswith('isHidden'):
                    is_hidden = True
                elif line.startswith('formatString:'):
                    format_string = line.split(':', 1)[1].strip().strip('"\'')
                elif line.startswith('sourceColumn:'):
                    source_column = line.split(':', 1)[1].strip()
                elif line.startswith('expression'):
                    # Calculated column
                    expr_match = re.search(r'expression\s*=\s*(.+?)(?=\n\s+[a-z]|\n\n|$)', block, re.DOTALL)
                    if expr_match:
                        expression = expr_match.group(1).strip()
            
            columns.append({
                'column_name': column_name,
                'data_type': data_type,
                'is_hidden': is_hidden,
                'format_string': format_string,
                'source_column': source_column,
                'expression': expression
            })
        
        return columns
    
    def parse_partition(self, table_file: Path) -> Optional[str]:
        """Extract Power Query M code from partition."""
        if not table_file.exists():
            return None
            
        content = table_file.read_text(encoding='utf-8-sig', errors='ignore')
        
        # Extract M expression from partition
        # Format: partition <name> = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\t<M code>
        # The M code is heavily indented with tabs
        
        # Find partition block
        partition_match = re.search(r'partition\s+[^\n]+=\s*m\s*\n(.+?)(?=\n\s*annotation|\n\s*$)', content, re.DOTALL)
        
        if partition_match:
            partition_content = partition_match.group(1)
            
            # Find the source = section
            source_match = re.search(r'source\s*=\s*\n(.+)', partition_content, re.DOTALL)
            
            if source_match:
                m_code = source_match.group(1)
                
                # Clean up indentation - remove leading tabs/spaces
                lines = m_code.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Remove leading whitespace but preserve relative indentation
                    stripped = line.lstrip('\t ')
                    if stripped:  # Only add non-empty lines
                        cleaned_lines.append(stripped)
                
                return '\n'.join(cleaned_lines).strip()
        
        return None
    
    def parse_hierarchy(self, root_path: Path) -> Dict:
        """Parse entire Power BI export hierarchy."""
        result = {
            'workspaces': [],
            'datasets': [],
            'data_objects': [],
            'data_sources': []
        }
        
        # Iterate through workspace folders
        if (root_path / "Raw Files").exists():
            workspace_root = root_path / "Raw Files"
        else:
            workspace_root = root_path
            
        for workspace_folder in workspace_root.iterdir():
            if not workspace_folder.is_dir():
                continue
                
            workspace = self.parse_workspace(workspace_folder)
            result['workspaces'].append(workspace)
            
            # Parse semantic models
            for item_folder in workspace_folder.glob("*.SemanticModel"):
                dataset = self.parse_dataset(item_folder, workspace.workspace_id)
                result['datasets'].append(dataset)
                
                # Parse tables
                data_objects = self.parse_data_objects(item_folder, dataset.dataset_id)
                result['data_objects'].extend(data_objects)
                
        return result
