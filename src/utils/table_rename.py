"""
Table Rename Module
Handles renaming tables and updating all references in Power BI semantic models
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from utils.backup_manager import backup_model_before_operation
from utils.pbir_connection_manager import set_all_reports_to_local

logger = logging.getLogger(__name__)


def _is_builtin_table(table_name: str) -> bool:
    """
    Check if table is a Power BI built-in auto-generated table
    
    Returns: True if table should be excluded from rename operations
    """
    # DateTableTemplate - auto-generated date table template
    if table_name.startswith('DateTableTemplate_'):
        return True
    
    # LocalDateTable - auto-generated date tables for date columns
    if table_name.startswith('LocalDateTable_'):
        return True
    
    # Other known built-in patterns can be added here
    
    return False


def get_tables_from_model(model_path: str) -> List[Dict]:
    """
    Get list of tables from a semantic model with columns and data types
    
    Returns: List of table dictionaries with name, file_path, columns, column_count, schema
    """
    tables = []
    definition_path = Path(model_path) / "definition"
    tables_path = definition_path / "tables"
    
    if not tables_path.exists():
        return tables
    
    # Read all .tmdl files in tables folder
    for table_file in tables_path.glob("*.tmdl"):
        table_name = table_file.stem
        
        # Filter out Power BI built-in auto-generated tables
        if _is_builtin_table(table_name):
            continue
        
        # Parse TMDL file to extract columns and schema
        columns = []
        schema = None  # Default to None, will be set if found in M query
        try:
            content = table_file.read_text(encoding='utf-8-sig')
            lines = content.split('\n')
            
            # Extract schema from M query (pattern: Schema="schemaname")
            schema_match = re.search(r'Schema\s*=\s*"([^"]+)"', content)
            if schema_match:
                schema = schema_match.group(1)
            
            in_column_section = False
            for line in lines:
                stripped = line.strip()
                
                # Detect column section
                if stripped.startswith('column '):
                    in_column_section = True
                    # Extract column name and data type
                    col_match = re.match(r"column\s+['\"](.*?)['\"]|column\s+(\w+)", stripped)
                    if col_match:
                        col_name = col_match.group(1) or col_match.group(2)
                        col_type = 'string'  # default
                        columns.append({'name': col_name, 'type': col_type})
                elif in_column_section and 'dataType:' in stripped:
                    # Extract data type from current column
                    if columns:
                        type_match = re.search(r'dataType:\s*(\w+)', stripped)
                        if type_match:
                            columns[-1]['type'] = type_match.group(1)
                elif stripped.startswith('measure ') or stripped.startswith('hierarchy ') or stripped.startswith('partition '):
                    in_column_section = False
        except Exception:
            pass  # If parsing fails, just return table with no columns
        
        tables.append({
            'name': table_name,
            'file_path': str(table_file),
            'columns': columns,
            'column_count': len(columns),
            'schema': schema  # Add schema to the returned data
        })
    
    return tables


def update_model_tmdl_references(model_path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
    """Update table references in model.tmdl file"""
    try:
        model_file = Path(model_path) / "definition" / "model.tmdl"
        if not model_file.exists():
            return True, "model.tmdl not found (optional)"
        
        content = model_file.read_text(encoding='utf-8-sig')
        
        # Update in PBI_QueryOrder annotation
        content = re.sub(
            r'(annotation\s+PBI_QueryOrder\s*=\s*\[)([^\]]+)(\])',
            lambda m: m.group(1) + m.group(2).replace(f'"{old_name}"', f'"{new_name}"') + m.group(3),
            content
        )
        
        # Update ref table statements - handle both quoted and unquoted names
        content = re.sub(
            r'^ref table\s+' + re.escape(old_name) + r'\s*$',
            f'ref table {new_name}',
            content,
            flags=re.MULTILINE
        )
        content = re.sub(
            r"^ref table\s+'" + re.escape(old_name) + r"'\s*$",
            f"ref table '{new_name}'",
            content,
            flags=re.MULTILINE
        )
        
        model_file.write_text(content, encoding='utf-8')
        return True, "Updated model.tmdl"
    except Exception as e:
        return False, f"Error updating model.tmdl: {str(e)}"


def update_relationships_tmdl(model_path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
    """Update table references in relationships.tmdl file"""
    try:
        rel_file = Path(model_path) / "definition" / "relationships.tmdl"
        if not rel_file.exists():
            return True, "relationships.tmdl not found (optional)"
        
        content = rel_file.read_text(encoding='utf-8-sig')
        
        # Update fromColumn and toColumn references
        # Pattern: TableName.ColumnName or 'Table Name'.ColumnName
        content = re.sub(
            r'\b' + re.escape(old_name) + r'\.',
            f'{new_name}.',
            content
        )
        content = re.sub(
            r"'" + re.escape(old_name) + r"'\.",
            f"'{new_name}'.",
            content
        )
        
        rel_file.write_text(content, encoding='utf-8')
        return True, "Updated relationships.tmdl"
    except Exception as e:
        return False, f"Error updating relationships.tmdl: {str(e)}"


def update_role_permissions(model_path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
    """Update table references in role .tmdl files"""
    try:
        roles_dir = Path(model_path) / "definition" / "roles"
        if not roles_dir.exists():
            return True, "No roles directory found (optional)"
        
        updated_roles = []
        for role_file in roles_dir.glob("*.tmdl"):
            content = role_file.read_text(encoding='utf-8-sig')
            original_content = content
            
            # Pattern 1: tablePermission TableName = expression
            content = re.sub(
                r'\btablePermission\s+' + re.escape(old_name) + r'\b',
                f'tablePermission {new_name}',
                content
            )
            
            # Pattern 2: References in DAX like 'TableName'[Column] or TableName[Column]
            content = re.sub(
                r"'" + re.escape(old_name) + r"'(\[)",
                f"'{new_name}'\\1",
                content
            )
            content = re.sub(
                r'\b' + re.escape(old_name) + r'(\[)',
                f'{new_name}\\1',
                content
            )
            
            if content != original_content:
                role_file.write_text(content, encoding='utf-8')
                updated_roles.append(role_file.name)
        
        if updated_roles:
            return True, f"Updated roles: {', '.join(updated_roles)}"
        return True, "No role permissions to update"
    except Exception as e:
        return False, f"Error updating role permissions: {str(e)}"


def update_report_visuals(model_path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
    """Update table references in report JSON files (visuals, filters, etc.)"""
    try:
        import json
        
        # Get the parent directory that might contain .Report folders
        model_parent = Path(model_path).parent
        updated_reports = []
        
        # Find all .Report folders at the same level as the .SemanticModel
        for report_dir in model_parent.glob("*.Report"):
            # Check for report.json files (legacy format)
            report_json = report_dir / "report.json"
            if report_json.exists():
                content = report_json.read_text(encoding='utf-8-sig')
                original_content = content
                
                # Pattern 1: \"Entity\":\"TableName\" (escaped JSON in config strings)
                content = re.sub(
                    r'\\"Entity\\"\s*:\s*\\"' + re.escape(old_name) + r'\\"',
                    f'\\"Entity\\":\\"{new_name}\\"',
                    content
                )
                
                # Pattern 2: \"Source\":\"TableName\" (escaped JSON for aliases)
                content = re.sub(
                    r'\\"Source\\"\s*:\s*\\"' + re.escape(old_name) + r'\\"',
                    f'\\"Source\\":\\"{new_name}\\"',
                    content
                )
                
                # Pattern 3: \"Name\":\"x\",\"Entity\":\"TableName\" (From clause)
                content = re.sub(
                    r'(\\"Name\\"\s*:\s*\\"[^"]+\\",\s*\\"Entity\\"\s*:\s*\\")' + re.escape(old_name) + r'(\\")',
                    f'\\1{new_name}\\2',
                    content
                )
                
                # Pattern 4: "Entity":"TableName" (direct JSON, not escaped - for filters array)
                content = re.sub(
                    r'"Entity"\s*:\s*"' + re.escape(old_name) + r'"',
                    f'"Entity":"{new_name}"',
                    content
                )
                
                # Pattern 5: "Source":"TableName" (direct JSON for aliases)
                content = re.sub(
                    r'"Source"\s*:\s*"' + re.escape(old_name) + r'"',
                    f'"Source":"{new_name}"',
                    content
                )
                
                # Pattern 6: "queryRef":"TableName.ColumnName" (escaped JSON)
                content = re.sub(
                    r'(\\"queryRef\\"\s*:\s*\\")' + re.escape(old_name) + r'(\.)([^\\]+)(\\")',
                    f'\\1{new_name}\\2\\3\\4',
                    content
                )
                
                # Pattern 7: "queryRef":"TableName.ColumnName" (direct JSON)
                content = re.sub(
                    r'("queryRef"\s*:\s*")' + re.escape(old_name) + r'(\.)([^"]+)(")',
                    f'\\1{new_name}\\2\\3\\4',
                    content
                )
                
                # Pattern 8: "queryRefs":["TableName.ColumnName"] (array format)
                content = re.sub(
                    r'(\["\s*)' + re.escape(old_name) + r'(\.)([^"]+)("\])',
                    f'\\1{new_name}\\2\\3\\4',
                    content
                )
                
                if content != original_content:
                    report_json.write_text(content, encoding='utf-8')
                    updated_reports.append(f"{report_dir.name}/report.json")
            
            # Check for definition/report.json (PBIP format)
            pbip_report_json = report_dir / "definition" / "report.json"
            if pbip_report_json.exists():
                content = pbip_report_json.read_text(encoding='utf-8-sig')
                original_content = content
                
                # Apply all patterns for escaped and direct JSON
                content = re.sub(
                    r'\\"Entity\\"\s*:\s*\\"' + re.escape(old_name) + r'\\"',
                    f'\\"Entity\\":\\"{new_name}\\"',
                    content
                )
                content = re.sub(
                    r'\\"Source\\"\s*:\s*\\"' + re.escape(old_name) + r'\\"',
                    f'\\"Source\\":\\"{new_name}\\"',
                    content
                )
                content = re.sub(
                    r'(\\"Name\\"\s*:\s*\\"[^"]+\\",\s*\\"Entity\\"\s*:\s*\\")' + re.escape(old_name) + r'(\\")',
                    f'\\1{new_name}\\2',
                    content
                )
                content = re.sub(
                    r'"Entity"\s*:\s*"' + re.escape(old_name) + r'"',
                    f'"Entity":"{new_name}"',
                    content
                )
                content = re.sub(
                    r'"Source"\s*:\s*"' + re.escape(old_name) + r'"',
                    f'"Source":"{new_name}"',
                    content
                )
                # Pattern 6: "queryRef":"TableName.ColumnName" (escaped JSON)
                content = re.sub(
                    r'(\\"queryRef\\"\s*:\s*\\")' + re.escape(old_name) + r'(\.)([^\\]+)(\\")',
                    f'\\1{new_name}\\2\\3\\4',
                    content
                )
                # Pattern 7: "queryRef":"TableName.ColumnName" (direct JSON)
                content = re.sub(
                    r'("queryRef"\s*:\s*")' + re.escape(old_name) + r'(\.)([^"]+)(")',
                    f'\\1{new_name}\\2\\3\\4',
                    content
                )
                
                # Pattern 8: "queryRefs":["TableName.ColumnName"] (array format)
                content = re.sub(
                    r'(\["\s*)' + re.escape(old_name) + r'(\.)([^"]+)("\])',
                    f'\\1{new_name}\\2\\3\\4',
                    content
                )
                
                if content != original_content:
                    pbip_report_json.write_text(content, encoding='utf-8')
                    updated_reports.append(f"{report_dir.name}/definition/report.json")
            
            # Check for page JSON files in definition/pages
            pages_dir = report_dir / "definition" / "pages"
            if pages_dir.exists():
                # Get all JSON files including visual.json files in subdirectories
                for page_json in pages_dir.rglob("*.json"):
                    content = page_json.read_text(encoding='utf-8-sig')
                    original_content = content
                    
                    # Apply all patterns
                    content = re.sub(
                        r'\\"Entity\\"\s*:\s*\\"' + re.escape(old_name) + r'\\"',
                        f'\\"Entity\\":\\"{new_name}\\"',
                        content
                    )
                    content = re.sub(
                        r'\\"Source\\"\s*:\s*\\"' + re.escape(old_name) + r'\\"',
                        f'\\"Source\\":\\"{new_name}\\"',
                        content
                    )
                    content = re.sub(
                        r'(\\"Name\\"\s*:\s*\\"[^"]+\\",\s*\\"Entity\\"\s*:\s*\\")' + re.escape(old_name) + r'(\\")',
                        f'\\1{new_name}\\2',
                        content
                    )
                    content = re.sub(
                        r'"Entity"\s*:\s*"' + re.escape(old_name) + r'"',
                        f'"Entity":"{new_name}"',
                        content
                    )
                    content = re.sub(
                        r'"Source"\s*:\s*"' + re.escape(old_name) + r'"',
                        f'"Source":"{new_name}"',
                        content
                    )
                    # Pattern 6: "queryRef":"TableName.ColumnName" (escaped JSON)
                    content = re.sub(
                        r'(\\"queryRef\\"\s*:\s*\\")' + re.escape(old_name) + r'(\.)([^\\]+)(\\")',
                        f'\\1{new_name}\\2\\3\\4',
                        content
                    )
                    # Pattern 7: "queryRef":"TableName.ColumnName" (direct JSON)
                    before_queryref = content
                    content = re.sub(
                        r'("queryRef"\s*:\s*")' + re.escape(old_name) + r'(\.)([^"]+)(")',
                        f'\\1{new_name}\\2\\3\\4',
                        content
                    )
                    if content != before_queryref:
                        logger.info(f"Updated queryRef references in {page_json.name}")
                    
                    # Pattern 8: "queryRefs":["TableName.ColumnName"] (array format)
                    before_queryrefs = content
                    content = re.sub(
                        r'(\[")\s*' + re.escape(old_name) + r'(\.)([^"]+)("\])',
                        f'\\1{new_name}\\2\\3\\4',
                        content
                    )
                    if content != before_queryrefs:
                        logger.info(f"Updated queryRefs array references in {page_json.name}")
                    
                    if content != original_content:
                        page_json.write_text(content, encoding='utf-8')
                        relative_path = page_json.relative_to(report_dir)
                        updated_reports.append(f"{report_dir.name}/{relative_path}")
                        logger.info(f"Updated file: {report_dir.name}/{relative_path}")
        
        if updated_reports:
            return True, f"Updated {len(updated_reports)} report files"
        return True, "No report files to update"
    except Exception as e:
        return False, f"Error updating report visuals: {str(e)}"


def update_all_table_dax_and_m_references(model_path: str, old_name: str, new_name: str, rename_backend: bool = True, old_schema: str = 'dbo', new_schema: str = 'dbo') -> Tuple[bool, str]:
    """Update table references in all measure/calculated column DAX expressions and M queries
    
    Args:
        model_path: Path to semantic model
        old_name: Current table name
        new_name: New table name
        rename_backend: If True, also rename M query table references. If False, only rename DAX references (display name).
        old_schema: Current schema name (default: 'dbo')
        new_schema: New schema name (default: 'dbo')
    """
    try:
        tables_path = Path(model_path) / "definition" / "tables"
        updated_count = 0
        
        if not tables_path.exists():
            return True, "No tables to update"
        
        for table_file in tables_path.glob("*.tmdl"):
            content = table_file.read_text(encoding='utf-8-sig')
            original = content
            
            # ===== ALWAYS UPDATE DAX REFERENCES (Display Name) =====
            
            # DAX Pattern 1: Table[Column]
            content = re.sub(
                r'\b' + re.escape(old_name) + r'(\[)',
                f'{new_name}\\1',
                content
            )
            
            # DAX Pattern 2: 'Table Name'[Column]
            content = re.sub(
                r"'" + re.escape(old_name) + r"'(\[)",
                f"'{new_name}'\\1",
                content
            )
            
            # DAX Pattern 3: Standalone table references (after parenthesis, comma, equals, RETURN)
            content = re.sub(r'(\()\s*' + re.escape(old_name) + r'\b(?!\[)', rf'\1{new_name}', content)
            content = re.sub(r'(,)\s*' + re.escape(old_name) + r'\b(?!\[)', rf',{new_name}', content)
            content = re.sub(r'(=)\s*' + re.escape(old_name) + r'\b(?!\[)', rf'={new_name}', content)
            content = re.sub(r'\bRETURN\s+' + re.escape(old_name) + r'\b(?!\[)', f'RETURN {new_name}', content, flags=re.IGNORECASE)
            
            # DAX Pattern 4: Quoted standalone table
            content = re.sub(r"([\(,=\s])'" + re.escape(old_name) + r"'(?!\[)", rf"\1'{new_name}'", content)
            
            # ===== CONDITIONALLY UPDATE M QUERY REFERENCES (Backend Table Name) =====
            # Only update if rename_backend is True (checkbox is checked)
            
            if rename_backend:
                # M Query Pattern 0: Schema="OldSchema" → Schema="NewSchema"
                if old_schema != new_schema:
                    content = re.sub(r'\bSchema\s*=\s*"' + re.escape(old_schema) + r'"', f'Schema="{new_schema}"', content)
                
                # M Query Pattern 1: Item="TableName" (in source references)
                content = re.sub(r'\bItem\s*=\s*"' + re.escape(old_name) + r'"', f'Item="{new_name}"', content)
                
                # M Query Pattern 2: Name="TableName" (in source references)
                content = re.sub(r'\bName\s*=\s*"' + re.escape(old_name) + r'"', f'Name="{new_name}"', content)
                
                # M Query Pattern 3: #"schema_TableName" (quoted identifiers with schema prefix)
                content = re.sub(r'(=\s*|,\s*)#"(\w+)_' + re.escape(old_name) + r'"', rf'\1#"\2_{new_name}"', content)
                
                # M Query Pattern 4: schema_TableName variables (with schema prefix, without quotes)
                content = re.sub(r'(=\s*|,\s*)(\w+)_' + re.escape(old_name) + r'\b(?!_)', rf'\1\2_{new_name}', content)
                
                # M Query Pattern 5: Plain variable names at line start (without schema prefix)
                # Matches: "    tablename = Source..." or "tablename = ..." at start of line with optional whitespace
                content = re.sub(r'^(\s*)' + re.escape(old_name) + r'\s*=\s*', rf'\1{new_name} = ', content, flags=re.MULTILINE)
                
                # M Query Pattern 6: Variable references in "in" clause
                # Matches: "in\n    tablename" or "in tablename" - preserves original whitespace
                content = re.sub(r'\bin(\s+)' + re.escape(old_name) + r'\b', rf'in\1{new_name}', content)
            
            if content != original:
                table_file.write_text(content, encoding='utf-8')
                updated_count += 1
        
        return True, f"Updated {updated_count} table file(s)"
    except Exception as e:
        return False, f"Error updating DAX/M: {str(e)}"


def rename_table(model_path: str, old_name: str, new_name: str, rename_backend: bool = True, old_schema: str = 'dbo', new_schema: str = 'dbo') -> Tuple[int, int, List[str]]:
    """
    Rename a table and update all references
    
    Args:
        model_path: Path to semantic model
        old_name: Current table name
        new_name: New table name
        rename_backend: If True, rename display name, .tmdl file, and M query table references (full rename).
                       If False, only rename display name (cosmetic rename, keeps backend name).
        old_schema: Current schema name (default: 'dbo')
        new_schema: New schema name (default: 'dbo')
    
    Returns: (success_count, error_count, error_messages)
    
    Behavior:
        When rename_backend=True (checkbox checked):
            - Changes display name: table OldName → table NewName
            - Renames file: OldName.tmdl → NewName.tmdl
            - Updates M query: Item="OldName" → Item="NewName"
            - Updates M query: Schema="OldSchema" → Schema="NewSchema"
            - Updates all DAX references
        
        When rename_backend=False (checkbox unchecked):
            - Changes display name: table OldName → table NewName
            - Keeps file: OldName.tmdl (unchanged)
            - Keeps M query: Item="OldName" (unchanged)
            - Updates all DAX references (they use display name)
    """
    errors = []
    success = 0
    
    try:
        tables_path = Path(model_path) / "definition" / "tables"
        old_file = tables_path / f"{old_name}.tmdl"
        
        if not old_file.exists():
            return 0, 1, [f"{old_name}: File not found"]
        
        # 1. Update table file content
        content = old_file.read_text(encoding='utf-8-sig')
        
        # Log original content snippet for debugging
        first_line = content.split('\n')[0] if content else ""
        logger.info(f"Original first line: '{first_line}'")
        logger.info(f"Looking for table declaration with old_name: '{old_name}'")
        
        # Update table name declaration (display name)
        # Pattern 1: table TableName (no quotes)
        pattern1 = r'^table\s+' + re.escape(old_name)
        content_after = re.sub(pattern1, f'table {new_name}', content, flags=re.MULTILINE)
        if content_after != content:
            logger.info(f"Pattern 1 matched: Changed 'table {old_name}' to 'table {new_name}'")
            content = content_after
        
        # Pattern 2: table 'TableName' (with quotes)
        pattern2 = r"^table\s+'" + re.escape(old_name) + r"'"
        content_after = re.sub(pattern2, f"table '{new_name}'", content, flags=re.MULTILINE)
        if content_after != content:
            logger.info(f"Pattern 2 matched: Changed \"table '{old_name}'\" to \"table '{new_name}'\"")
            content = content_after
        
        # Log result
        first_line_after = content.split('\n')[0] if content else ""
        logger.info(f"Updated first line: '{first_line_after}'")
        
        # Rename the .tmdl file only if rename_backend is True
        # When False: only display name changes (in content), file stays with backend name
        if rename_backend:
            # Full rename: change both display name AND backend (file + M query)
            new_file = tables_path / f"{new_name}.tmdl"
            
            # Update content first, then rename file atomically
            old_file.write_text(content, encoding='utf-8')
            
            # Check if we actually need to rename (not just content update)
            if old_name != new_name:
                # Handle case-only renames on Windows (case-insensitive filesystem)
                if old_name.lower() == new_name.lower():
                    # Case-only rename: use temporary intermediate name
                    temp_file = tables_path / f"{new_name}_temp_rename_{id(old_file)}.tmdl"
                    old_file.rename(temp_file)
                    temp_file.rename(new_file)
                    logger.info(f"Case-only rename: {old_name}.tmdl → {new_name}.tmdl (via temp)")
                else:
                    # Normal rename: atomic operation
                    old_file.rename(new_file)
                    logger.info(f"Full rename: {old_name}.tmdl → {new_name}.tmdl (display + backend)")
            else:
                logger.info(f"Content updated (no filename change): {old_file.name}")
        else:
            # Cosmetic rename: only display name changes, keep backend name (file + M query)
            old_file.write_text(content, encoding='utf-8')
            logger.info(f"Display name only: Updated 'table {new_name}' in {old_file.name} (backend unchanged)")
        
        success += 1
        
        # 2. Update model.tmdl references
        model_success, model_msg = update_model_tmdl_references(model_path, old_name, new_name)
        if not model_success:
            errors.append(model_msg)
        
        # 3. Update relationships.tmdl
        rel_success, rel_msg = update_relationships_tmdl(model_path, old_name, new_name)
        if not rel_success:
            errors.append(rel_msg)
        
        # 4. Update role permissions
        role_success, role_msg = update_role_permissions(model_path, old_name, new_name)
        if not role_success:
            errors.append(role_msg)
        
        # 5. Update report visuals
        report_success, report_msg = update_report_visuals(model_path, old_name, new_name)
        if not report_success:
            errors.append(report_msg)
        
        # 6. Update DAX expressions and M queries in all tables
        # Pass rename_backend to control M query table name updates
        # Pass old_schema and new_schema to update Schema parameter in M queries
        dax_success, dax_msg = update_all_table_dax_and_m_references(model_path, old_name, new_name, rename_backend, old_schema, new_schema)
        if not dax_success:
            errors.append(dax_msg)
        
        return success, len(errors), errors
        
    except Exception as e:
        return 0, 1, [f"{old_name}: {str(e)}"]


def rename_tables_bulk(model_path: str, rename_mapping: Dict[str, any], rename_backend: bool = True, with_schema: bool = False) -> Tuple[int, int, List[str]]:
    """
    Rename multiple tables at once
    
    Args:
        model_path: Path to semantic model
        rename_mapping: Dictionary mapping old_name -> new_name (str) or old_name -> {'new_name': str, 'old_schema': str, 'new_schema': str} (dict)
        rename_backend: If True, rename display name, .tmdl files, and M query references (full rename).
                       If False, only rename display names (cosmetic rename, keeps backend names).
        with_schema: If True, rename_mapping contains schema information (dict structure)
    
    Returns: (success_count, error_count, error_messages)
    
    Process:
        1. Creates backup in BACKUP/Workspace/Model_table_rename_timestamp/
        2. Sets all reports to local connections
        3. Renames tables according to rename_backend setting:
           - When True: Full rename (display + file + M query + schema)
           - When False: Display only (cosmetic rename)
    """
    all_errors = []
    
    # Step 1: Create backup before any modifications
    logger.info(f"Creating backup for model: {model_path}")
    backup_success, backup_result = backup_model_before_operation(model_path, "table_rename")
    
    if not backup_success:
        all_errors.append(f"⚠️ Backup warning: {backup_result} (continuing anyway)")
        logger.warning(f"Backup failed: {backup_result}")
    else:
        logger.info(f"Backup created: {backup_result}")
    
    # Step 2: Set all reports to point to local semantic model
    logger.info("Setting reports to local connections...")
    success_reports, error_reports = set_all_reports_to_local(model_path)
    if success_reports > 0:
        logger.info(f"Set {success_reports} report(s) to local connection")
    if error_reports > 0:
        all_errors.append(f"⚠️ Could not update {error_reports} report connection(s) to local")
    
    # Step 3: Perform table renames
    total_success = 0
    total_errors = 0
    
    for old_name, rename_data in rename_mapping.items():
        # Handle both old format (string) and new format (dict)
        if with_schema and isinstance(rename_data, dict):
            new_name = rename_data['new_name']
            old_schema = rename_data.get('old_schema', 'dbo')
            new_schema = rename_data.get('new_schema', old_schema)
        else:
            new_name = rename_data if isinstance(rename_data, str) else rename_data.get('new_name', old_name)
            old_schema = 'dbo'
            new_schema = 'dbo'
        
        if old_name != new_name or old_schema != new_schema:
            success, error_count, errors = rename_table(model_path, old_name, new_name, rename_backend, old_schema, new_schema)
            total_success += success
            total_errors += error_count
            all_errors.extend(errors)
    
    return total_success, total_errors, all_errors
