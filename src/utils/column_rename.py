"""
Column Rename Module
Handles renaming columns and updating all references in Power BI semantic models
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from utils.backup_manager import backup_model_before_operation
from utils.pbir_connection_manager import set_all_reports_to_local

logger = logging.getLogger(__name__)


def snake_to_pascal(text: str) -> str:
    """Convert snake_case to PascalCase"""
    words = text.replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in words if word)


def pascal_to_snake(text: str) -> str:
    """Convert PascalCase to snake_case"""
    result = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', result).lower()


def camel_to_pascal(text: str) -> str:
    """Convert camelCase to PascalCase"""
    if text:
        return text[0].upper() + text[1:]
    return text


def pascal_to_camel(text: str) -> str:
    """Convert PascalCase to camelCase"""
    if text:
        return text[0].lower() + text[1:]
    return text


def kebab_to_pascal(text: str) -> str:
    """Convert kebab-case to PascalCase"""
    words = text.split('-')
    return ''.join(word.capitalize() for word in words if word)


def snake_to_camel(text: str) -> str:
    """Convert snake_case to camelCase"""
    words = text.split('_')
    if not words:
        return text
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:] if word)


def apply_column_transformation(column_name: str, transformation: str, prefix: str = "", suffix: str = "") -> str:
    """
    Apply transformation to column name
    
    Args:
        column_name: Original column name
        transformation: Type of transformation
        prefix: Prefix to add
        suffix: Suffix to add
    
    Returns: Transformed column name
    """
    result = column_name
    
    # Apply transformation
    if transformation == "snake_to_pascal":
        result = snake_to_pascal(result)
    elif transformation == "pascal_to_snake":
        result = pascal_to_snake(result)
    elif transformation == "camel_to_pascal":
        result = camel_to_pascal(result)
    elif transformation == "pascal_to_camel":
        result = pascal_to_camel(result)
    elif transformation == "kebab_to_pascal":
        result = kebab_to_pascal(result)
    elif transformation == "snake_to_camel":
        result = snake_to_camel(result)
    elif transformation == "uppercase":
        result = result.upper()
    elif transformation == "lowercase":
        result = result.lower()
    elif transformation == "title_case":
        result = result.title()
    elif transformation == "remove_spaces":
        result = result.replace(' ', '')
    elif transformation == "spaces_to_underscores":
        result = result.replace(' ', '_')
    elif transformation == "remove_prefix":
        # Remove common prefixes
        for pfx in ['col_', 'fld_', 'dim_', 'fact_']:
            if result.lower().startswith(pfx):
                result = result[len(pfx):]
                break
    elif transformation == "remove_suffix":
        # Remove common suffixes
        for sfx in ['_id', '_key', '_name', '_date']:
            if result.lower().endswith(sfx):
                result = result[:-len(sfx)]
                break
    
    # Apply prefix and suffix
    if prefix:
        result = prefix + result
    if suffix:
        result = result + suffix
    
    return result


def get_columns_from_table(table_file_path: str) -> List[Dict]:
    """
    Get list of columns from a table TMDL file
    
    Returns: List of column dictionaries with name, type, source_name
    """
    columns = []
    table_file = Path(table_file_path)
    
    if not table_file.exists():
        logger.warning(f"Table file not found: {table_file_path}")
        return columns
    
    try:
        content = table_file.read_text(encoding='utf-8-sig')
        lines = content.split('\n')
        
        current_column = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect column section (starts with 'column ')
            if stripped.startswith('column ') and not current_column:
                # Extract column name
                col_match = re.match(r"column\s+['\"](.*?)['\"]|column\s+(\w+)", stripped)
                if col_match:
                    col_name = col_match.group(1) or col_match.group(2)
                    current_column = {
                        'name': col_name,
                        'type': 'string',
                        'source_name': col_name,
                        'is_calculated': False
                    }
                    logger.debug(f"Found column: {col_name}")
            elif current_column:
                # Check if we've moved to a new section (measure, hierarchy, partition, etc.)
                if stripped.startswith(('measure ', 'hierarchy ', 'partition ')):
                    # Save current column and reset
                    columns.append(current_column)
                    current_column = None
                # Check if it's a new column
                elif stripped.startswith('column '):
                    # Save current column
                    columns.append(current_column)
                    # Create new column
                    col_match = re.match(r"column\s+['\"](.*?)['\"]|column\s+(\w+)", stripped)
                    if col_match:
                        col_name = col_match.group(1) or col_match.group(2)
                        current_column = {
                            'name': col_name,
                            'type': 'string',
                            'source_name': col_name,
                            'is_calculated': False
                        }
                else:
                    # We're inside a column definition, extract properties
                    # Extract data type
                    if 'dataType:' in stripped:
                        type_match = re.search(r'dataType:\s*(\w+)', stripped)
                        if type_match:
                            current_column['type'] = type_match.group(1)
                    
                    # Check if it's a calculated column (has expression)
                    if 'expression' in stripped:
                        current_column['is_calculated'] = True
                    
                    # Extract source name
                    if 'sourceColumn:' in stripped:
                        source_match = re.search(r'sourceColumn:\s*["\']?([^"\']+)["\']?', stripped)
                        if source_match:
                            current_column['source_name'] = source_match.group(1)
        
        # Add last column if still open
        if current_column:
            columns.append(current_column)
            logger.debug(f"Added last column: {current_column['name']}")
        
        logger.info(f"Parsed {len(columns)} columns from {table_file.name}")
    except Exception as e:
        logger.error(f"Error parsing columns from {table_file_path}: {e}")
    
    return columns


def update_column_in_table_file(table_file_path: str, old_name: str, new_name: str, rename_source_column: bool = False) -> Tuple[bool, str]:
    """Update column definition in table TMDL file
    
    Args:
        table_file_path: Path to the table TMDL file
        old_name: Current column name
        new_name: New column name
        rename_source_column: If True, also rename sourceColumn property (for backend column renames)
    """
    try:
        table_file = Path(table_file_path)
        if not table_file.exists():
            return False, f"Table file not found: {table_file_path}"
        
        content = table_file.read_text(encoding='utf-8-sig')
        original = content
        
        # Pattern 1: column definition line
        # Match both: column ColumnName and column 'Column Name'
        content = re.sub(
            r'^(\s*)column\s+' + re.escape(old_name) + r'\b',
            rf'\1column {new_name}',
            content,
            flags=re.MULTILINE
        )
        content = re.sub(
            r"^(\s*)column\s+'" + re.escape(old_name) + r"'",
            rf"\1column '{new_name}'",
            content,
            flags=re.MULTILINE
        )
        
        # Pattern 2: References in DAX expressions (measures, calculated columns, calculated tables)
        # Table[OldColumn] -> Table[NewColumn]
        content = re.sub(
            r'\[' + re.escape(old_name) + r'\]',
            f'[{new_name}]',
            content
        )
        
        # Pattern 3: sourceColumn - optionally rename if backend column changed
        if rename_source_column:
            content = re.sub(
                r'sourceColumn:\s*"' + re.escape(old_name) + r'"',
                f'sourceColumn: "{new_name}"',
                content
            )
        
        if content != original:
            table_file.write_text(content, encoding='utf-8')
            return True, "Updated table file"
        else:
            return True, "No changes needed in table file"
    except Exception as e:
        return False, f"Error updating table file: {str(e)}"


def update_column_references_in_all_tables(model_path: str, table_name: str, old_col_name: str, new_col_name: str) -> Tuple[bool, str]:
    """Update column references in all tables' DAX expressions (measures, calculated columns)"""
    try:
        tables_path = Path(model_path) / "definition" / "tables"
        updated_count = 0
        
        if not tables_path.exists():
            return True, "No tables to update"
        
        for table_file in tables_path.glob("*.tmdl"):
            content = table_file.read_text(encoding='utf-8-sig')
            original = content
            
            # DAX Pattern 1: TableName[ColumnName]
            content = re.sub(
                r'\b' + re.escape(table_name) + r'\[' + re.escape(old_col_name) + r'\]',
                f'{table_name}[{new_col_name}]',
                content
            )
            
            # DAX Pattern 2: 'Table Name'[ColumnName]
            content = re.sub(
                r"'" + re.escape(table_name) + r"'\[" + re.escape(old_col_name) + r"\]",
                f"'{table_name}'[{new_col_name}]",
                content
            )
            
            # DAX Pattern 3: RELATED('Table'[Column])
            content = re.sub(
                r'RELATED\s*\(\s*' + re.escape(table_name) + r'\[' + re.escape(old_col_name) + r'\]\s*\)',
                f'RELATED({table_name}[{new_col_name}])',
                content,
                flags=re.IGNORECASE
            )
            content = re.sub(
                r"RELATED\s*\(\s*'" + re.escape(table_name) + r"'\[" + re.escape(old_col_name) + r"\]\s*\)",
                f"RELATED('{table_name}'[{new_col_name}])",
                content,
                flags=re.IGNORECASE
            )
            
            if content != original:
                table_file.write_text(content, encoding='utf-8')
                updated_count += 1
        
        return True, f"Updated {updated_count} table file(s)"
    except Exception as e:
        return False, f"Error updating DAX references: {str(e)}"


def update_relationships_for_column(model_path: str, table_name: str, old_col_name: str, new_col_name: str) -> Tuple[bool, str]:
    """Update column references in relationships.tmdl file"""
    try:
        rel_file = Path(model_path) / "definition" / "relationships.tmdl"
        if not rel_file.exists():
            return True, "relationships.tmdl not found (optional)"
        
        content = rel_file.read_text(encoding='utf-8-sig')
        original = content
        
        # Update fromColumn and toColumn references
        # Pattern: fromColumn: TableName.ColumnName or 'Table Name'.ColumnName
        content = re.sub(
            r'\b' + re.escape(table_name) + r'\.' + re.escape(old_col_name) + r'\b',
            f'{table_name}.{new_col_name}',
            content
        )
        content = re.sub(
            r"'" + re.escape(table_name) + r"'\." + re.escape(old_col_name) + r'\b',
            f"'{table_name}'.{new_col_name}",
            content
        )
        
        if content != original:
            rel_file.write_text(content, encoding='utf-8')
            return True, "Updated relationships.tmdl"
        else:
            return True, "No changes needed in relationships.tmdl"
    except Exception as e:
        return False, f"Error updating relationships: {str(e)}"


def update_report_visuals_for_column(model_path: str, table_name: str, old_col_name: str, new_col_name: str) -> Tuple[bool, str]:
    """Update column references in report JSON files (visuals, filters, etc.)"""
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
                
                # Pattern 1: \"Entity\":\"TableName\",\"Property\":\"ColumnName\" (escaped JSON in config strings)
                content = re.sub(
                    r'(\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"\s*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                # Pattern 2: "Entity":"TableName"}..."Property":"ColumnName" (direct JSON with flexible whitespace/newlines)
                content = re.sub(
                    r'("Entity"\s*:\s*"' + re.escape(table_name) + r'"[^}]*}[^"]*"Property"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
                    content,
                    flags=re.DOTALL
                )
                
                # Pattern 3: {\"Expression\":{\"SourceRef\":{\"Entity\":\"TableName\"}},\"Property\":\"ColumnName\"}
                content = re.sub(
                    r'(\\{[^}]*\\"Expression\\"[^}]*\\"SourceRef\\"[^}]*\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"[^}]*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                # Pattern 4: {"Expression":{"SourceRef":{"Entity":"TableName"}},"Property":"ColumnName"}
                content = re.sub(
                    r'(\\{[^}]*\\"Expression\\"[^}]*\\"SourceRef\\"[^}]*\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"[^}]*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                # Pattern 5: "queryRef":"TableName.ColumnName" (escaped JSON)
                content = re.sub(
                    r'(\\"queryRef\\"\s*:\s*\\"' + re.escape(table_name) + r'\.)' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                # Pattern 6: "queryRef":"TableName.ColumnName" (direct JSON)
                content = re.sub(
                    r'("queryRef"\s*:\s*"' + re.escape(table_name) + r'\.)' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                # Pattern 7: "nativeQueryRef":"ColumnName" (direct JSON)
                content = re.sub(
                    r'("nativeQueryRef"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
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
                    r'(\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"\s*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                # Pattern 2: "Entity":"TableName"}..."Property":"ColumnName" (direct JSON with flexible whitespace/newlines)
                content = re.sub(
                    r'("Entity"\s*:\s*"' + re.escape(table_name) + r'"[^}]*}[^"]*"Property"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
                    content,
                    flags=re.DOTALL
                )
                content = re.sub(
                    r'(\\{[^}]*\\"Expression\\"[^}]*\\"SourceRef\\"[^}]*\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"[^}]*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                content = re.sub(
                    r'(\{[^}]*"Expression"[^}]*"SourceRef"[^}]*"Entity"\s*:\s*"' + re.escape(table_name) + r'"[^}]*}\s*,\s*"Property"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                # Pattern 5: "queryRef":"TableName.ColumnName" (escaped JSON)
                content = re.sub(
                    r'(\\"queryRef\\"\s*:\s*\\"' + re.escape(table_name) + r'\.)' + re.escape(old_col_name) + r'(\\")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                # Pattern 6: "queryRef":"TableName.ColumnName" (direct JSON)
                content = re.sub(
                    r'("queryRef"\s*:\s*"' + re.escape(table_name) + r'\.)' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                # Pattern 7: "nativeQueryRef":"ColumnName" (direct JSON)
                content = re.sub(
                    r'("nativeQueryRef"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                    f'\\1{new_col_name}\\2',
                    content
                )
                
                if content != original_content:
                    pbip_report_json.write_text(content, encoding='utf-8')
                    updated_reports.append(f"{report_dir.name}/definition/report.json")
            
            # Check for page JSON files in definition/pages
            pages_dir = report_dir / "definition" / "pages"
            if pages_dir.exists():
                for page_json in pages_dir.rglob("*.json"):
                    content = page_json.read_text(encoding='utf-8-sig')
                    original_content = content
                    
                    # Apply all patterns
                    content = re.sub(
                        r'(\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"\s*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                        f'\\1{new_col_name}\\2',
                        content
                    )
                    # Pattern 2: "Entity":"TableName"}..."Property":"ColumnName" (direct JSON with flexible whitespace/newlines)
                    content = re.sub(
                        r'("Entity"\s*:\s*"' + re.escape(table_name) + r'"[^}]*}[^"]*"Property"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                        f'\\1{new_col_name}\\2',
                        content,
                        flags=re.DOTALL
                    )
                    content = re.sub(
                        r'(\\{[^}]*\\"Expression\\"[^}]*\\"SourceRef\\"[^}]*\\"Entity\\"\s*:\s*\\"' + re.escape(table_name) + r'\\"[^}]*}\s*,\s*\\"Property\\"\s*:\s*\\")' + re.escape(old_col_name) + r'(\\")',
                        f'\\1{new_col_name}\\2',
                        content
                    )
                    content = re.sub(
                        r'(\{[^}]*"Expression"[^}]*"SourceRef"[^}]*"Entity"\s*:\s*"' + re.escape(table_name) + r'"[^}]*}\s*,\s*"Property"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                        f'\\1{new_col_name}\\2',
                        content
                    )
                    # Pattern 5: "queryRef":"TableName.ColumnName" (escaped JSON)
                    content = re.sub(
                        r'(\\"queryRef\\"\s*:\s*\\"' + re.escape(table_name) + r'\.)' + re.escape(old_col_name) + r'(\\")',
                        f'\\1{new_col_name}\\2',
                        content
                    )
                    # Pattern 6: "queryRef":"TableName.ColumnName" (direct JSON)
                    content = re.sub(
                        r'("queryRef"\s*:\s*"' + re.escape(table_name) + r'\.)' + re.escape(old_col_name) + r'(")',
                        f'\\1{new_col_name}\\2',
                        content
                    )
                    
                    # Pattern 7: "nativeQueryRef":"ColumnName" (direct JSON)
                    content = re.sub(
                        r'("nativeQueryRef"\s*:\s*")' + re.escape(old_col_name) + r'(")',
                        f'\\1{new_col_name}\\2',
                        content
                    )
                    
                    if content != original_content:
                        page_json.write_text(content, encoding='utf-8')
                        updated_reports.append(f"{report_dir.name}/definition/pages/{page_json.name}")
        
        if updated_reports:
            return True, f"Updated {len(updated_reports)} report file(s): {', '.join(updated_reports)}"
        else:
            return True, "No report files needed updates"
    except Exception as e:
        return False, f"Error updating report visuals: {str(e)}"


def rename_column(model_path: str, table_name: str, old_col_name: str, new_col_name: str, rename_source_column: bool = False, update_visuals: bool = True) -> Tuple[int, int, List[str]]:
    """
    Rename a column and update all references
    
    Args:
        model_path: Path to semantic model
        table_name: Name of the table containing the column
        old_col_name: Current column name
        new_col_name: New column name
        rename_source_column: If True, also rename sourceColumn property (for backend column renames)
        update_visuals: If True, update report visual references (controlled by checkbox)
    
    Returns: (success_count, error_count, error_messages)
    """
    errors = []
    success = 0
    
    try:
        # Get table file path
        table_file_path = Path(model_path) / "definition" / "tables" / f"{table_name}.tmdl"
        
        if not table_file_path.exists():
            return 0, 1, [f"{table_name}: Table file not found"]
        
        # 1. Update column definition in the table file
        table_success, table_msg = update_column_in_table_file(str(table_file_path), old_col_name, new_col_name, rename_source_column)
        if not table_success:
            errors.append(table_msg)
        else:
            success += 1
        
        # 2. Update references in all other tables (DAX measures, calculated columns)
        dax_success, dax_msg = update_column_references_in_all_tables(model_path, table_name, old_col_name, new_col_name)
        if not dax_success:
            errors.append(dax_msg)
        
        # 3. Update relationships
        rel_success, rel_msg = update_relationships_for_column(model_path, table_name, old_col_name, new_col_name)
        if not rel_success:
            errors.append(rel_msg)
        
        # 4. Update report visuals (report.json files) - controlled by checkbox
        if update_visuals:
            report_success, report_msg = update_report_visuals_for_column(model_path, table_name, old_col_name, new_col_name)
            if not report_success:
                errors.append(report_msg)
            else:
                logger.info(f"Report update: {report_msg}")
        else:
            logger.info(f"Skipping report visual updates (checkbox unchecked)")
        
        return success, len(errors), errors
        
    except Exception as e:
        return 0, 1, [f"{table_name}.{old_col_name}: {str(e)}"]


def rename_columns_bulk(model_path: str, rename_mapping: Dict[str, Dict[str, str]], rename_source_column: bool = False, update_visuals: bool = True) -> Tuple[int, int, List[str]]:
    """
    Rename multiple columns at once
    
    Args:
        model_path: Path to semantic model
        rename_mapping: Dictionary mapping table_name -> {old_col_name: new_col_name}
        rename_source_column: If True, also rename sourceColumn property (for backend column renames)
        update_visuals: If True, update report visual references (controlled by checkbox)
    
    Returns: (success_count, error_count, error_messages)
    """
    all_errors = []
    
    # Step 1: Create backup before any modifications
    logger.info(f"Creating backup for model: {model_path}")
    backup_success, backup_result = backup_model_before_operation(model_path, "column_rename")
    
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
    
    # Step 3: Perform column renames
    total_success = 0
    total_errors = 0
    
    for table_name, column_mappings in rename_mapping.items():
        for old_col_name, new_col_name in column_mappings.items():
            if old_col_name != new_col_name:
                success, error_count, errors = rename_column(model_path, table_name, old_col_name, new_col_name, rename_source_column, update_visuals)
                total_success += success
                total_errors += error_count
                all_errors.extend(errors)
    
    return total_success, total_errors, all_errors
