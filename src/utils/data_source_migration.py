"""
Data Source Migration Module
Handles extraction, mapping, and migration of data sources in Power BI semantic models
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import shutil
from datetime import datetime
import difflib
import logging

from utils.pbir_connection_manager import set_all_reports_to_local

# ============================================================================
# 1. DATA SOURCE TEMPLATES
# ============================================================================

DATA_SOURCE_TEMPLATES = {
    "SQL_Server": {
        "display_name": "SQL Server / Azure SQL",
        "parameters": ["server", "database"],
        "m_template": '''let
	Source = Sql.Database("{server}", "{database}"),
	{schema_line}
	{table_name} = Source{{{table_reference}}}
in
	{table_name}''',
        "connection_string_pattern": r'Sql\.Database\("([^"]+)",\s*"([^"]+)"\)'
    },
    
    "Azure_SQL": {
        "display_name": "Azure SQL Database",
        "parameters": ["server", "database"],
        "m_template": '''let
	Source = Sql.Database("{server}", "{database}"),
	{schema_line}
	{table_name} = Source{{{table_reference}}}
in
	{table_name}''',
        "connection_string_pattern": r'Sql\.Database\("([^"]+)",\s*"([^"]+)"\)'
    },
    
    "Snowflake": {
        "display_name": "Snowflake",
        "parameters": ["server", "warehouse", "database"],
        "m_template": '''let
	Source = Snowflake.Databases("{server}", "{warehouse}"),
	{database_name}_Database = Source{{{database_reference}}},
	{schema_name}_Schema = {database_name}_Database{{{schema_reference}}},
	{table_name} = {schema_name}_Schema{{{table_reference}}}
in
	{table_name}''',
        "connection_string_pattern": r'Snowflake\.Databases\("([^"]+)",\s*"([^"]+)"\)'
    },
    
    "Lakehouse": {
        "display_name": "Fabric Lakehouse (SQL Endpoint)",
        "parameters": ["server", "database"],
        "m_template": '''let
	Source = Sql.Database("{server}", "{database}"),
	{schema_line}
	{table_name} = Source{{{table_reference}}}
in
	{table_name}''',
        "connection_string_pattern": r'Sql\.Database\("([^"]+)",\s*"([^"]+)"\)'
    },
    
    "Excel": {
        "display_name": "Excel Workbook",
        "parameters": ["file_path"],
        "m_template": '''let
	Source = Excel.Workbook(File.Contents("{file_path}"), null, true),
	{table_name}_Sheet = Source{{{sheet_reference}}}
in
	{table_name}_Sheet''',
        "connection_string_pattern": r'Excel\.Workbook\(File\.Contents\("([^"]+)"\)'
    }
}

# ============================================================================
# 2. SOURCE DETECTOR
# ============================================================================

def detect_data_sources(model_path: str) -> List[Dict]:
    """
    Parse semantic model and extract all data sources with their details
    
    Returns: List of data sources with table mappings
    [
        {
            'source_type': 'SQL_Server',
            'connection_details': {'server': 'server.com', 'database': 'db'},
            'tables': [
                {'name': 'Sales', 'schema': 'dbo', 'file_path': '...'},
                ...
            ]
        }
    ]
    """
    sources = []
    tables_path = Path(model_path) / "definition" / "tables"
    
    if not tables_path.exists():
        return sources
    
    # Track unique sources
    source_map = {}
    
    for table_file in tables_path.glob("*.tmdl"):
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract partition M query - handle both formats:
            # Format 1: partition X = m\n\tsource = ```...```
            # Format 2: partition X = m\n\tmode: import\n\tsource =\n\t\tlet...
            # Handle partition names with spaces in quotes: 'Currency Exchange-123'
            partition_match = re.search(
                r"partition\s+(?:'[^']+'|\"[^\"]+\"|\S+)\s*=\s*m\s*\n.*?source\s*=\s*\n(.*?)(?=\n\n|\npartition|\nannotation PBI_ResultType|\Z)", 
                content, re.DOTALL
            )
            
            if not partition_match:
                continue
            
            m_query = partition_match.group(1)
            table_name = table_file.stem
            
            # Detect source type and extract details
            source_info = _detect_source_type(m_query)
            
            if source_info:
                source_key = f"{source_info['source_type']}_{json.dumps(source_info['connection_details'], sort_keys=True)}"
                
                if source_key not in source_map:
                    source_map[source_key] = {
                        'source_type': source_info['source_type'],
                        'connection_details': source_info['connection_details'],
                        'tables': []
                    }
                
                source_map[source_key]['tables'].append({
                    'name': table_name,
                    'schema': source_info.get('schema', ''),
                    'file_path': str(table_file),
                    'm_query': m_query
                })
        
        except Exception as e:
            print(f"Error processing {table_file}: {e}")
            continue
    
    return list(source_map.values())

def _detect_source_type(m_query: str) -> Optional[Dict]:
    """Detect source type from M query and extract connection details"""
    
    # SQL Server / Azure SQL
    sql_match = re.search(r'Sql\.Database\("([^"]+)",\s*"([^"]+)"\)', m_query)
    if sql_match:
        server, database = sql_match.groups()
        schema_match = re.search(r'\[Schema="([^"]+)"\]', m_query)
        schema = schema_match.group(1) if schema_match else 'dbo'
        
        source_type = "Azure_SQL" if "database.windows.net" in server else "SQL_Server"
        
        return {
            'source_type': source_type,
            'connection_details': {
                'server': server,
                'database': database,
                'schema': schema
            },
            'schema': schema
        }
    
    # Snowflake
    snowflake_match = re.search(r'Snowflake\.Databases\("([^"]+)",\s*"([^"]+)"\)', m_query)
    if snowflake_match:
        account, warehouse = snowflake_match.groups()
        db_match = re.search(r'\[Name="([^"]+)",\s*Kind="Database"\]', m_query)
        schema_match = re.search(r'\[Name="([^"]+)",\s*Kind="Schema"\]', m_query)
        
        return {
            'source_type': 'Snowflake',
            'connection_details': {
                'account': account,
                'warehouse': warehouse,
                'database': db_match.group(1) if db_match else '',
                'schema': schema_match.group(1) if schema_match else 'PUBLIC'
            },
            'schema': schema_match.group(1) if schema_match else 'PUBLIC'
        }
    
    # Lakehouse
    lakehouse_match = re.search(r'Lakehouse\.Shortcuts\("([^"]+)",\s*"([^"]+)"\)', m_query)
    if lakehouse_match:
        workspace_id, lakehouse_id = lakehouse_match.groups()
        return {
            'source_type': 'Lakehouse',
            'connection_details': {
                'workspace_id': workspace_id,
                'lakehouse_id': lakehouse_id
            }
        }
    
    # CSV files
    csv_match = re.search(r'Csv\.Document\(File\.Contents\("([^"]+)"\)', m_query)
    if csv_match:
        file_path = csv_match.group(1)
        return {
            'source_type': 'CSV',
            'connection_details': {
                'file_path': file_path
            }
        }
    
    # Excel files
    excel_match = re.search(r'Excel\.Workbook\(File\.Contents\("([^"]+)"\)', m_query)
    if excel_match:
        file_path = excel_match.group(1)
        return {
            'source_type': 'Excel',
            'connection_details': {
                'file_path': file_path
            }
        }
    
    # JSON files
    json_match = re.search(r'Json\.Document\(File\.Contents\("([^"]+)"\)', m_query)
    if json_match:
        file_path = json_match.group(1)
        return {
            'source_type': 'JSON',
            'connection_details': {
                'file_path': file_path
            }
        }
    
    return None

# ============================================================================
# 3. M QUERY GENERATOR
# ============================================================================

def generate_new_m_query(
    table_name: str,
    old_source_type: str,
    new_source_type: str,
    new_connection_details: Dict,
    schema: str = "",
    original_m_query: str = None
) -> str:
    """
    Update M query with new connection details while preserving transformation steps.
    Only replaces the Source and table extraction lines, keeps all transformations.
    """
    
    # If we have the original query, preserve all transformation steps
    if original_m_query:
        server = new_connection_details.get('server', '')
        database = new_connection_details.get('database', '')
        
        # Parse the original query to extract transformation steps
        lines = original_m_query.split('\n')
        
        # Find where transformations start (lines with #"..." transformations)
        transformation_start_idx = None
        source_var_name = None  # The variable that the first transformation references
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Find transformation steps (start with #")
            if stripped.startswith('#"'):
                transformation_start_idx = i
                # Extract what variable this transformation uses (e.g., "dbo_Product_Table" in the example)
                # Pattern: #"Step" = Table.Something(previous_variable, ...)
                match = re.search(r'Table\.\w+\((\w+)', stripped)
                if match:
                    source_var_name = match.group(1)
                break
        
        # Build new source section based on target type
        new_source_lines = []
        table_var_name = table_name.replace(' ', '_').replace('-', '_')
        
        if new_source_type in ["SQL_Server", "Azure_SQL", "Lakehouse"]:
            # SQL Server / Azure SQL / Lakehouse SQL Endpoint - all use same Sql.Database pattern
            new_source_lines.append('				let')
            new_source_lines.append(f'				    Source = Sql.Database("{server}", "{database}"),')
            
            # All SQL-based sources use: {[Schema="schema",Item="table"]}[Data]
            schema_actual = schema or 'dbo'
            new_source_lines.append(f'				    {table_var_name} = Source{{[Schema="{schema_actual}",Item="{table_name}"]}}[Data]')
            
            # If there's a comma needed (transformations follow), add it
            if transformation_start_idx:
                new_source_lines[-1] += ','
        
        elif new_source_type == "Excel":
            # Excel pattern: Excel.Workbook + [Item="sheet", Kind="Table"]
            file_path = new_connection_details.get('file_path', '')
            new_source_lines.append('				let')
            new_source_lines.append(f'				    Source = Excel.Workbook(File.Contents("{file_path}"), null, true),')
            
            # Excel uses: {[Item="sheet_name", Kind="Table"]}[Data]
            # Try to preserve original Item name from the old query
            sheet_item = table_name  # Default to table name
            for line in lines[:5]:  # Check first few lines
                match = re.search(r'\[Item="([^"]+)".*Kind="Table"\]', line)
                if match:
                    sheet_item = match.group(1)
                    break
            
            new_source_lines.append(f'				    {table_var_name} = Source{{[Item="{sheet_item}",Kind="Table"]}}[Data]')
            
            # If there's a comma needed (transformations follow), add it
            if transformation_start_idx:
                new_source_lines[-1] += ','
        
        elif new_source_type == "Snowflake":
            # Snowflake pattern: multi-level hierarchy with Database -> Schema -> Table
            # Reference: https://learn.microsoft.com/en-us/power-query/connectors/snowflake
            warehouse = new_connection_details.get('warehouse', '')
            new_source_lines.append('				let')
            new_source_lines.append(f'				    Source = Snowflake.Databases("{server}", "{warehouse}"),')
            
            # Create variable names (replace special characters)
            db_var = database.replace('-', '_').replace(' ', '_').replace('.', '_') + '_Database'
            schema_var = (schema or 'PUBLIC').replace('-', '_').replace(' ', '_').replace('.', '_') + '_Schema'
            table_var = table_name.replace('-', '_').replace(' ', '_').replace('.', '_') + '_Table'
            
            # Snowflake uses: {[Name="...", Kind="Database|Schema|Table"]}
            new_source_lines.append(f'				    {db_var} = Source{{[Name="{database}",Kind="Database"]}},')
            new_source_lines.append(f'				    {schema_var} = {db_var}{{[Name="{schema or "PUBLIC"}",Kind="Schema"]}},')
            new_source_lines.append(f'				    {table_var} = {schema_var}{{[Name="{table_name}",Kind="Table"]}}[Data]')
            
            # Update table_var_name for transformation variable replacement
            table_var_name = table_var
            
            # If there's a comma needed (transformations follow), add it
            if transformation_start_idx:
                new_source_lines[-1] += ','
        
        # Preserve all transformation steps (except PromoteHeaders when migrating from CSV/Excel to relational DB)
        if transformation_start_idx:
            skip_promote_headers = (old_source_type in ["Excel", "CSV"] and 
                                   new_source_type in ["SQL_Server", "Azure_SQL", "Lakehouse", "Snowflake"])
            
            promoted_var = None  # The variable assigned to PromoteHeaders
            source_before_promote = None  # The variable PromoteHeaders uses (e.g., Sheet)
            
            for i in range(transformation_start_idx, len(lines)):
                line = lines[i]
                stripped = line.strip()
                
                # Skip PromoteHeaders step when migrating from Excel to relational DB
                if skip_promote_headers and 'Table.PromoteHeaders' in stripped:
                    # Extract: promoted_var = Table.PromoteHeaders(source_var, ...)
                    # Pattern 1: #"Step Name" = Table.PromoteHeaders(source_var, ...)
                    match = re.match(r'\s*#"([^"]+)"\s*=\s*Table\.PromoteHeaders\(([^,\)]+)', stripped)
                    if match:
                        promoted_var = f'#"{match.group(1)}"'  # e.g., #"Promoted Headers"
                        source_before_promote = match.group(2).strip()  # e.g., CategoryMaster_Sheet
                    else:
                        # Pattern 2: variable_name = Table.PromoteHeaders(source_var, ...)
                        match = re.match(r'\s*(\w+)\s*=\s*Table\.PromoteHeaders\(([^,\)]+)', stripped)
                        if match:
                            promoted_var = match.group(1)  # e.g., CategoryMaster_Promoted
                            source_before_promote = match.group(2).strip()  # e.g., CategoryMaster_Sheet
                    continue
                
                # Update variable references
                if source_var_name and source_var_name != table_var_name:
                    line = line.replace(source_var_name, table_var_name)
                
                # If we skipped PromoteHeaders, replace references to promoted_var with the new table_var_name
                if promoted_var and table_var_name:
                    # Replace references like: (#"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", ...))
                    # With: (#"Changed Type" = Table.TransformColumnTypes(DimCategoryMaster, ...))
                    if promoted_var in line:
                        line = line.replace(promoted_var, table_var_name)
                
                # Add newline after commas for better readability
                if line.rstrip().endswith(','):
                    new_source_lines.append(line)
                else:
                    new_source_lines.append(line)
        else:
            # No transformations found, just close with "in" statement
            new_source_lines.append('				in')
            new_source_lines.append(f'				    {table_var_name}')
        
        return '\n'.join(new_source_lines)
    
    # Generate from template if no original query
    return _generate_from_template(table_name, new_source_type, new_connection_details, schema)


def _generate_from_template(
    table_name: str,
    new_source_type: str,
    new_connection_details: Dict,
    schema: str = ""
) -> str:
    """Generate complete M query from template (fallback when no original query)"""
    template_info = DATA_SOURCE_TEMPLATES.get(new_source_type)
    if not template_info:
        raise ValueError(f"Unknown source type: {new_source_type}")
    
    template = template_info['m_template']
    
    # Prepare template variables - don't escape backslashes
    # M query uses single backslashes, TMDL format handles escaping
    variables = {
        'table_name': table_name.replace(' ', '_'),
    }
    
    # Use connection details as-is (single backslashes in M query)
    for key, value in new_connection_details.items():
        variables[key] = value
    
    # Handle schema references
    if schema and '{schema_line}' in template:
        if new_source_type in ["SQL_Server", "Azure_SQL"]:
            variables['schema_line'] = f'{schema}_Schema = Source{{[Schema="{schema}"]}},'
            variables['table_reference'] = f'[Schema="{schema}", Item="{table_name}"]'
        elif new_source_type == "Snowflake":
            variables['database_name'] = new_connection_details.get('database', 'DB').replace('-', '_')
            variables['schema_name'] = schema.replace('-', '_')
            variables['database_reference'] = f'[Name="{new_connection_details.get("database", "")}", Kind="Database"]'
            variables['schema_reference'] = f'[Name="{schema}", Kind="Schema"]'
            variables['table_reference'] = f'[Name="{table_name}", Kind="Table"]'
        elif new_source_type == "Lakehouse":
            variables['schema_line'] = f'{schema}_Schema = Source{{[Name="{schema}", Kind="Schema"]}},' if schema else ''
            variables['table_reference'] = f'[Name="{table_name}", Kind="Table"]'
    else:
        variables['schema_line'] = ''
        if new_source_type in ["SQL_Server", "Azure_SQL"]:
            variables['table_reference'] = f'[Item="{table_name}"]'
        elif new_source_type == "Snowflake":
            variables['database_name'] = new_connection_details.get('database', 'DB').replace('-', '_')
            variables['schema_name'] = new_connection_details.get('schema', 'PUBLIC').replace('-', '_')
            variables['database_reference'] = f'[Name="{new_connection_details.get("database", "")}", Kind="Database"]'
            variables['schema_reference'] = f'[Name="{new_connection_details.get("schema", "PUBLIC")}", Kind="Schema"]'
            variables['table_reference'] = f'[Name="{table_name}", Kind="Table"]'
        elif new_source_type == "Excel":
            sheet_name = new_connection_details.get('sheet_name', table_name)
            variables['sheet_reference'] = f'[Item="{sheet_name}", Kind="Sheet"]'
        elif new_source_type == "Dataverse":
            variables['entity_reference'] = f'[Name="{table_name}"]'
        else:
            variables['table_reference'] = f'[Name="{table_name}"]'
    
    # Format template
    try:
        m_query = template.format(**variables)
        return m_query
    except KeyError as e:
        raise ValueError(f"Missing required parameter: {e}")

# ============================================================================
# 4. SOURCE VALIDATION
# ============================================================================

def validate_target_source(
    new_source_type: str,
    new_connection_details: Dict,
    tables: List[str]
) -> Tuple[bool, str, List[str]]:
    """
    Validate that tables exist in the target source
    
    Returns: (is_valid, message, missing_tables)
    """
    # This is a placeholder - actual implementation would connect to the source
    # For now, we'll return success with a warning
    
    missing_tables = []
    
    if new_source_type in ["SQL_Server", "Azure_SQL"]:
        message = f"⚠️ Validation: Please verify tables exist in {new_connection_details.get('database', 'target database')}"
    elif new_source_type == "Snowflake":
        message = f"⚠️ Validation: Please verify tables exist in {new_connection_details.get('database', '')}.{new_connection_details.get('schema', '')}"
    elif new_source_type == "Lakehouse":
        message = "⚠️ Validation: Please verify tables exist in target Lakehouse"
    elif new_source_type == "Excel":
        message = "⚠️ Validation: Please verify sheet names match table names in Excel file"
    else:
        message = "⚠️ Validation: Please verify tables exist in target source"
    
    return True, message, missing_tables

# ============================================================================
# 5. MIGRATION EXECUTOR
# ============================================================================

def migrate_table_source(
    table_file_path: str,
    new_m_query: str
) -> Tuple[bool, str]:
    """
    Update the table file with new M query
    """
    try:
        with open(table_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the partition source - handle both formats (including partition names with spaces in quotes and GUID suffixes)
        pattern = r"(partition\s+(?:'[^']+'|\"[^\"]+\"|[\w-]+)\s*=\s*m\s*\n.*?source\s*=\s*\n)(.*?)(?=\n\n|\npartition|\nannotation PBI_ResultType|\Z)"
        
        def replacer(match):
            partition_header = match.group(1)
            # The new_m_query already has proper indentation and starts with 'let'
            return partition_header + new_m_query
        
        new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
        
        if new_content == content:
            return False, "No partition found to update"
        
        with open(table_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, "Table source updated successfully"
    
    except Exception as e:
        return False, f"Error updating table: {str(e)}"

def backup_model_before_migration(model_path: str, export_root: Path) -> Tuple[bool, str]:
    """
    Create a backup of the model before migration
    
    Args:
        model_path: Path to the model being migrated
        export_root: Root export folder containing Raw Files (can pass model_path, will find export root)
    
    Returns: (success, backup_path_or_error_message)
    """
    def copy_with_error_handling(src, dst):
        """Copy directory tree with error handling for long paths and special characters"""
        errors = []
        src = Path(src)
        dst = Path(dst)
        
        try:
            # Create destination directory
            dst.mkdir(parents=True, exist_ok=True)
            
            # Walk through source directory
            for item in src.rglob('*'):
                try:
                    # Calculate relative path and target
                    rel_path = item.relative_to(src)
                    target = dst / rel_path
                    
                    # Skip if path is too long (Windows MAX_PATH limitation)
                    if len(str(target)) > 250:
                        errors.append((str(item), str(target), "Path too long (>250 chars), skipping"))
                        continue
                    
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        # Ensure parent directory exists
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target)
                        
                except Exception as e:
                    errors.append((str(item), str(target), str(e)))
                    continue
                    
        except Exception as e:
            errors.append((str(src), str(dst), str(e)))
            
        return errors
    
    try:
        model_path = Path(model_path)
        
        # Find the export root (goes up to find the folder containing Raw Files or FabricExport)
        current = model_path
        export_root = None
        while current.parent != current:
            if (current / "Raw Files").exists() or current.name.startswith("FabricExport_"):
                export_root = current
                break
            current = current.parent
        
        if not export_root:
            return False, "Could not find export root folder"
        
        # Extract workspace and model names
        workspace_name = model_path.parent.name
        model_name = model_path.name
        
        # Create BACKUP folder structure: BACKUP/WorkspaceName/ModelName_migration_timestamp/
        backup_root = export_root / "BACKUP" / workspace_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup folder name: ModelName_migration_timestamp
        backup_folder_name = f"{model_name}_migration_{timestamp}"
        backup_path = backup_root / backup_folder_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy the semantic model with error handling
        errors = copy_with_error_handling(model_path, backup_path / model_name)
        
        # Check and copy report if exists (same name pattern: ModelName.Report)
        workspace_path = model_path.parent
        report_name = model_name.replace('.SemanticModel', '.Report')
        report_path = workspace_path / report_name
        if report_path.exists():
            report_errors = copy_with_error_handling(report_path, backup_path / report_name)
            errors.extend(report_errors)
        
        if errors:
            logging.warning(f"Backup completed with {len(errors)} errors/warnings: {errors[:3]}...")  # Log first 3 errors
            return True, str(backup_path)  # Still return success but log warnings
        else:
            logging.info(f"Backup created: {backup_path}")
            return True, str(backup_path)
    
    except Exception as e:
        logging.error(f"Backup failed: {str(e)}")
        return False, f"Backup failed: {str(e)}"


def scan_backups(export_path: str) -> List[Dict]:
    """
    Scan BACKUP folder and return list of available backups
    
    Args:
        export_path: Root export folder path
    
    Returns: List of backup info dictionaries
    [
        {
            'workspace': 'MyWorkspace',
            'model_name': 'Sales Model',
            'backup_path': '.../BACKUP/MyWorkspace/Sales Model_20241219_143022/',
            'timestamp': '2024-12-19 14:30:22',
            'has_semantic_model': True,
            'has_report': True,
            'size_mb': 15.4
        }
    ]
    """
    backups = []
    backup_root = Path(export_path) / "BACKUP"
    
    if not backup_root.exists():
        return backups
    
    try:
        # Structure: BACKUP/WorkspaceName/ModelName_timestamp/
        for workspace_folder in backup_root.iterdir():
            if not workspace_folder.is_dir():
                continue
                
            workspace_name = workspace_folder.name
            
            for backup_folder in workspace_folder.iterdir():
                if not backup_folder.is_dir():
                    continue
                
                try:
                    # Parse folder name: ModelName_YYYYMMDD_HHMMSS
                    folder_name = backup_folder.name
                    parts = folder_name.rsplit('_', 2)  # Split from right to get timestamp
                    
                    if len(parts) >= 3:
                        model_name = parts[0]
                        date_str = parts[1]
                        time_str = parts[2]
                        
                        # Format timestamp
                        timestamp_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                    else:
                        model_name = folder_name
                        timestamp_str = "Unknown"
                    
                    # Check what's backed up
                    has_semantic_model = False
                    has_report = False
                    
                    for item in backup_folder.iterdir():
                        if item.is_dir():
                            if item.suffix == '.SemanticModel':
                                has_semantic_model = True
                            elif item.suffix == '.Report':
                                has_report = True
                    
                    # Calculate backup size
                    size_bytes = sum(f.stat().st_size for f in backup_folder.rglob('*') if f.is_file())
                    size_mb = size_bytes / (1024 * 1024)
                    
                    backups.append({
                        'workspace': workspace_name,
                        'model_name': model_name,
                        'backup_path': str(backup_folder),
                        'timestamp': timestamp_str,
                        'has_semantic_model': has_semantic_model,
                        'has_report': has_report,
                        'size_mb': round(size_mb, 2)
                    })
                    
                except Exception as e:
                    logging.warning(f"Error processing backup folder {backup_folder}: {e}")
                    continue
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
    except Exception as e:
        logging.error(f"Error scanning backups: {e}")
    
    return backups


def restore_from_backup(
    backup_path: str,
    target_path: str,
    restore_semantic_model: bool = True,
    restore_report: bool = False
) -> Tuple[int, int, List[str]]:
    """
    Restore semantic model and/or report from backup
    
    Args:
        backup_path: Path to backup folder
        target_path: Target path in Raw Files (workspace folder)
        restore_semantic_model: Whether to restore .SemanticModel
        restore_report: Whether to restore .Report
    
    Returns: (success_count, error_count, errors_list)
    """
    errors = []
    success_count = 0
    error_count = 0
    
    try:
        backup_path = Path(backup_path)
        target_path = Path(target_path)
        
        if not backup_path.exists():
            return 0, 1, [f"Backup path not found: {backup_path}"]
        
        # Find items to restore
        items_to_restore = []
        
        logging.info(f"Scanning backup folder: {backup_path}")
        for item in backup_path.iterdir():
            logging.info(f"  Found item: {item.name} (is_dir={item.is_dir()})")
            if not item.is_dir():
                continue
            
            if restore_semantic_model and item.name.endswith('.SemanticModel'):
                items_to_restore.append(('semantic_model', item))
                logging.info(f"    -> Added for restore: Semantic Model")
            elif restore_report and item.name.endswith('.Report'):
                items_to_restore.append(('report', item))
                logging.info(f"    -> Added for restore: Report")
        
        if not items_to_restore:
            available_items = [f.name for f in backup_path.iterdir() if f.is_dir()]
            return 0, 1, [f"No items selected for restore. Available items: {', '.join(available_items)}"]
        
        # Restore each item
        for item_type, item in items_to_restore:
            try:
                dest = target_path / item.name
                
                logging.info(f"Restoring {item_type}: {item.name} -> {dest}")
                
                # Check if destination exists
                if dest.exists():
                    # Remove existing (we're restoring over it)
                    logging.info(f"  Removing existing: {dest}")
                    shutil.rmtree(dest)
                
                # Copy from backup to target
                shutil.copytree(item, dest)
                success_count += 1
                logging.info(f"  ✓ Successfully restored {item_type}")
                
            except Exception as e:
                error_count += 1
                error_msg = f"Failed to restore {item.name}: {str(e)}"
                errors.append(error_msg)
                logging.error(f"  ✗ {error_msg}")
        
        return success_count, error_count, errors
    
    except Exception as e:
        return 0, 1, [f"Restore failed: {str(e)}"]

def migrate_all_tables(
    source_info: Dict,
    new_source_type: str,
    new_connection_details: Dict,
    dest_model_path: str,
    table_name_mapping: Dict[str, str] = None,
    skip_backup: bool = False
) -> Tuple[int, int, List[str]]:
    """
    Migrate all tables from one source to another within a specific semantic model.
    
    IMPORTANT: This function ONLY processes tables that are listed in source_info['tables'].
    It will NOT touch tables from other sources or models. This ensures proper isolation
    when migrating multiple semantic models or sources.
    
    Args:
        source_info: Source information with tables list (only these tables will be migrated)
        new_source_type: Target source type
        new_connection_details: New connection parameters
        dest_model_path: Destination model path (must match the model containing the source)
        table_name_mapping: Optional dict mapping old_name -> new_name
        skip_backup: If True, skip backup creation (useful when backup is handled externally)
    
    Returns: (success_count, error_count, error_messages)
    """
    success_count = 0
    error_count = 0
    errors = []
    
    # Create backup before migration (unless skipped)
    if not skip_backup:
        backup_success, backup_result = backup_model_before_migration(dest_model_path, Path(dest_model_path))
        if not backup_success:
            errors.append(f"⚠️ Backup warning: {backup_result} (continuing anyway)")
    
    # Get tables path for this specific model
    tables_path = Path(dest_model_path) / "definition" / "tables"
    if not tables_path.exists():
        return 0, 1, [f"Tables folder not found: {tables_path}"]
    
    logging.info(f"=== MIGRATE_ALL_TABLES START ===")
    logging.info(f"Model Path: {dest_model_path}")
    logging.info(f"Model Name: {Path(dest_model_path).name}")
    logging.info(f"Tables Path: {tables_path}")
    logging.info(f"Source Type: {source_info['source_type']}")
    logging.info(f"Source Info - Tables to migrate: {[t['name'] for t in source_info['tables']]}")
    
    # CRITICAL VALIDATION: Verify this source belongs to this model
    # Get all actual table files in this model
    actual_table_files = {f.stem for f in tables_path.glob("*.tmdl")}
    logging.info(f"Actual tables in model: {actual_table_files}")
    
    # Check if source tables match this model
    source_table_names = {t['name'] for t in source_info['tables']}
    tables_not_in_model = source_table_names - actual_table_files
    if tables_not_in_model:
        error_msg = f"CRITICAL: Source contains tables that don't exist in this model: {tables_not_in_model}"
        logging.error(error_msg)
        logging.error(f"This indicates tables from another model are being processed!")
        return 0, len(tables_not_in_model), [error_msg]
    
    # CRITICAL: Only process tables that are explicitly in the selected source
    # This prevents table mixing between different semantic models or data sources
    for table_info in source_info['tables']:
        try:
            original_name = table_info['name']
            current_name = table_name_mapping.get(original_name, original_name) if table_name_mapping else original_name
            
            logging.info(f"Processing table: {original_name} (current: {current_name})")
            
            # Find the actual file (might have been renamed)
            table_file = tables_path / f"{current_name}.tmdl"
            
            # If not found with current name, try original name
            if not table_file.exists():
                table_file = tables_path / f"{original_name}.tmdl"
            
            # Skip if file doesn't exist IN THIS MODEL
            if not table_file.exists():
                error_count += 1
                error_msg = f"{original_name}: File not found in {tables_path.parent.parent.name} (looked for {current_name}.tmdl and {original_name}.tmdl)"
                logging.warning(error_msg)
                errors.append(error_msg)
                continue
            
            logging.info(f"Found table file: {table_file}")
            
            # Get schema and original M query
            schema = table_info.get('schema', 'dbo')
            original_m_query = table_info.get('m_query', None)
            
            # Generate new M query with current table name (already renamed)
            new_m_query = generate_new_m_query(
                table_name=current_name,  # Use current file name
                old_source_type=source_info['source_type'],
                new_source_type=new_source_type,
                new_connection_details=new_connection_details,
                schema=schema,
                original_m_query=original_m_query
            )
            
            # Update the table with new M query
            success, message = migrate_table_source(str(table_file), new_m_query)
            
            if success:
                success_count += 1
                logging.info(f"✓ Successfully migrated: {current_name}")
            else:
                error_count += 1
                errors.append(f"{current_name}: {message}")
                logging.error(f"✗ Failed to migrate {current_name}: {message}")
        
        except Exception as e:
            error_count += 1
            error_msg = f"{original_name}: {str(e)}"
            errors.append(error_msg)
            logging.error(f"Exception migrating {original_name}: {str(e)}")
    
    logging.info(f"=== MIGRATE_ALL_TABLES END ===")
    logging.info(f"Success: {success_count}, Errors: {error_count}")
    
    # After successful migration, update .pbir connections to point to local semantic model
    if success_count > 0:
        try:
            # Call set_all_reports_to_local with the model path (it finds workspace automatically)
            pbir_success_count, pbir_error_count = set_all_reports_to_local(dest_model_path)
            if pbir_success_count > 0:
                logging.info(f"Updated {pbir_success_count} .pbir connection(s) to local semantic model")
            if pbir_error_count > 0:
                logging.warning(f"Failed to update {pbir_error_count} .pbir connection(s)")
        except Exception as e:
            # Non-critical, don't fail the migration
            logging.warning(f"Failed to update .pbir connections: {str(e)}")
    
    return success_count, error_count, errors


def preview_migration(
    source_info: Dict,
    new_source_type: str,
    new_connection_details: Dict,
    dest_model_path: str,
    table_name_mapping: Dict[str, str] = None
) -> Dict:
    """
    Generate preview of migration changes WITHOUT modifying files
    
    Args:
        source_info: Source information with tables list
        new_source_type: Target source type
        new_connection_details: New connection parameters
        dest_model_path: Destination model path
        table_name_mapping: Optional dict mapping old_name -> new_name
    
    Returns: Preview dictionary with file changes
    {
        'model_path': str,
        'model_name': str,
        'source_type_from': str,
        'source_type_to': str,
        'files_to_change': [
            {
                'file_path': str,
                'relative_path': str,
                'table_name': str,
                'old_content': str,
                'new_content': str,
                'unified_diff': str,
                'lines_added': int,
                'lines_removed': int,
                'lines_changed': int
            }
        ],
        'summary': {
            'total_files': int,
            'total_tables': int,
            'total_lines_changed': int,
            'connection_changes': dict
        }
    }
    """
    preview = {
        'model_path': dest_model_path,
        'model_name': Path(dest_model_path).name,
        'source_type_from': source_info['source_type'],
        'source_type_to': new_source_type,
        'files_to_change': [],
        'summary': {
            'total_files': 0,
            'total_tables': 0,
            'total_lines_changed': 0,
            'connection_changes': new_connection_details
        }
    }
    
    tables_path = Path(dest_model_path) / "definition" / "tables"
    if not tables_path.exists():
        return preview
    
    # Process each table to generate preview
    for table_info in source_info['tables']:
        try:
            original_name = table_info['name']
            current_name = table_name_mapping.get(original_name, original_name) if table_name_mapping else original_name
            
            # Find the actual file
            table_file = tables_path / f"{current_name}.tmdl"
            if not table_file.exists():
                table_file = tables_path / f"{original_name}.tmdl"
            
            if not table_file.exists():
                continue
            
            # Read current content
            old_content = table_file.read_text(encoding='utf-8')
            
            # Generate new M query
            schema = table_info.get('schema', 'dbo')
            original_m_query = table_info.get('m_query', None)
            
            new_m_query = generate_new_m_query(
                table_name=current_name,
                old_source_type=source_info['source_type'],
                new_source_type=new_source_type,
                new_connection_details=new_connection_details,
                schema=schema,
                original_m_query=original_m_query
            )
            
            # Generate new content (simulate migration)
            new_content = _simulate_migration(old_content, new_m_query)
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"{table_file.name} (Before)",
                tofile=f"{table_file.name} (After)",
                lineterm=''
            ))
            unified_diff = ''.join(diff_lines)
            
            # Count changes (skip diff headers starting with +++, ---, @@)
            lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            lines_changed = lines_added + lines_removed
            
            # Add to preview
            preview['files_to_change'].append({
                'file_path': str(table_file),
                'relative_path': str(table_file.relative_to(Path(dest_model_path))),
                'table_name': current_name,
                'old_content': old_content,
                'new_content': new_content,
                'unified_diff': unified_diff,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'lines_changed': lines_changed
            })
            
            preview['summary']['total_lines_changed'] += lines_changed
            
        except Exception as e:
            logging.warning(f"Preview generation failed for {original_name}: {e}")
            continue
    
    preview['summary']['total_files'] = len(preview['files_to_change'])
    preview['summary']['total_tables'] = len(preview['files_to_change'])
    
    return preview


def _simulate_migration(old_content: str, new_m_query: str) -> str:
    """
    Simulate migration by replacing M query in content
    (Same logic as migrate_table_source but returns new content instead of writing)
    """
    # Find and replace the partition source - handle both formats (including partition names with spaces in quotes and GUID suffixes)
    pattern = r"(partition\s+(?:'[^']+'|\"[^\"]+\"|[\w-]+)\s*=\s*m\s*\n.*?source\s*=\s*\n)(.*?)(?=\n\n|\npartition|\nannotation PBI_ResultType|\Z)"
    
    def replacer(match):
        partition_header = match.group(1)
        # The new_m_query already has proper indentation and starts with 'let'
        return partition_header + new_m_query
    
    new_content = re.sub(pattern, replacer, old_content, flags=re.DOTALL)
    
    return new_content


def export_preview_report(preview: Dict, output_path: str) -> bool:
    """
    Export preview to HTML report
    
    Args:
        preview: Preview dictionary from preview_migration()
        output_path: Path to save HTML report
    
    Returns: Success boolean
    """
    try:
        html_diff = difflib.HtmlDiff(tabsize=4, wrapcolumn=80)
        
        # Build HTML report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Migration Preview - {preview['model_name']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #0078D4; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .summary {{ background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .file-section {{ background: white; padding: 15px; border-radius: 5px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .file-header {{ font-size: 18px; font-weight: bold; color: #0078D4; margin-bottom: 10px; }}
        .stats {{ display: flex; gap: 20px; margin: 10px 0; }}
        .stat {{ padding: 10px; background: #f0f0f0; border-radius: 3px; }}
        .stat-label {{ font-size: 12px; color: #666; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #0078D4; }}
        table.diff {{ border-collapse: collapse; width: 100%; font-family: 'Courier New', monospace; font-size: 12px; }}
        .diff_header {{ background-color: #e0e0e0; }}
        .diff_next {{ background-color: #c0c0c0; }}
        .diff_add {{ background-color: #d4ffd4; }}
        .diff_chg {{ background-color: #ffffaa; }}
        .diff_sub {{ background-color: #ffd4d4; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Migration Preview Report</h1>
        <p><strong>Model:</strong> {preview['model_name']}</p>
        <p><strong>Migration:</strong> {preview['source_type_from']} → {preview['source_type_to']}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Files to Change</div>
                <div class="stat-value">{preview['summary']['total_files']}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Tables Affected</div>
                <div class="stat-value">{preview['summary']['total_tables']}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Total Lines Changed</div>
                <div class="stat-value">{preview['summary']['total_lines_changed']}</div>
            </div>
        </div>
        
        <h3>🔗 Connection Changes</h3>
        <ul>
"""
        
        for param, value in preview['summary']['connection_changes'].items():
            html += f"            <li><strong>{param}:</strong> {value}</li>\n"
        
        html += """        </ul>
    </div>
"""
        
        # Add file diffs
        for file_change in preview['files_to_change']:
            html += f"""
    <div class="file-section">
        <div class="file-header">📄 {file_change['table_name']}.tmdl</div>
        <p><strong>Path:</strong> {file_change['relative_path']}</p>
        <p><strong>Changes:</strong> <span style="color: green;">+{file_change['lines_added']}</span> / <span style="color: red;">-{file_change['lines_removed']}</span></p>
        
        {html_diff.make_table(
            file_change['old_content'].splitlines(),
            file_change['new_content'].splitlines(),
            fromdesc='Before Migration',
            todesc='After Migration',
            context=True,
            numlines=3
        )}
    </div>
"""
        
        html += """
</body>
</html>"""
        
        # Write to file
        Path(output_path).write_text(html, encoding='utf-8')
        return True
        
    except Exception as e:
        logging.error(f"Failed to export preview report: {e}")
        return False

