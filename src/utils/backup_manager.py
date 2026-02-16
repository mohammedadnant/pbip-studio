"""
Backup Manager Module
Centralized backup management for all model operations (datasource migration, table rename, column rename)
"""

import shutil
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def backup_model_before_operation(model_path: str, operation_type: str = "operation") -> Tuple[bool, str]:
    """
    Create a backup of the model before any operation
    
    Args:
        model_path: Path to the model being modified
        operation_type: Type of operation (e.g., "migration", "table_rename", "column_rename")
    
    Returns: (success, backup_path_or_error_message)
    """
    try:
        model_path = Path(model_path)
        
        # Find the export root (goes up to find the folder containing Raw Files)
        export_root = _find_export_root(model_path)
        
        if not export_root:
            return False, "Could not locate export root folder"
        
        # Create BACKUP folder structure
        backup_root = export_root / "BACKUP"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get workspace and model name from path
        workspace_name, model_name = _extract_workspace_and_model(model_path)
        
        # Create backup path: BACKUP/WorkspaceName/ModelName_operation_timestamp/
        backup_folder_name = f"{model_name}_{operation_type}_{timestamp}"
        backup_path = backup_root / workspace_name / backup_folder_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating backup at: {backup_path}")
        
        # Copy the entire model folder (.SemanticModel)
        semantic_model_dest = backup_path / model_path.name
        shutil.copytree(model_path, semantic_model_dest, dirs_exist_ok=True)
        logger.info(f"  ✓ Backed up semantic model: {model_path.name}")
        
        # Also backup the corresponding .Report folder if it exists
        report_path = model_path.parent / model_path.name.replace('.SemanticModel', '.Report')
        if report_path.exists() and report_path.is_dir():
            report_dest = backup_path / report_path.name
            shutil.copytree(report_path, report_dest, dirs_exist_ok=True)
            logger.info(f"  ✓ Backed up report: {report_path.name}")
        else:
            logger.info(f"  ℹ No report folder found at: {report_path}")
        
        logger.info(f"Backup created successfully: {backup_path}")
        return True, str(backup_path)
    
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False, f"Backup failed: {str(e)}"


def _find_export_root(model_path: Path) -> Optional[Path]:
    """Find the export root folder containing Raw Files"""
    current = model_path
    max_depth = 10  # Safety limit
    depth = 0
    
    while current.parent != current and depth < max_depth:
        if (current / "Raw Files").exists() or current.name.startswith("FabricExport_"):
            return current
        current = current.parent
        depth += 1
    
    return None


def _extract_workspace_and_model(model_path: Path) -> Tuple[str, str]:
    """Extract workspace and model names from path"""
    try:
        parts = model_path.parts
        raw_files_idx = parts.index("Raw Files")
        workspace_name = parts[raw_files_idx + 1]
        model_folder_name = parts[raw_files_idx + 2]
        
        # Remove .SemanticModel suffix if present to get clean model name
        model_name = model_folder_name.replace('.SemanticModel', '').replace('.Report', '')
        return workspace_name, model_name
    except (ValueError, IndexError):
        # Fallback: use last two parts
        workspace_name = model_path.parent.name
        model_folder_name = model_path.name
        model_name = model_folder_name.replace('.SemanticModel', '').replace('.Report', '')
        return workspace_name, model_name


def scan_backups(export_path: str) -> List[Dict]:
    """
    Scan BACKUP folder and return list of available backups
    
    Args:
        export_path: Root export folder path
    
    Returns: List of backup info dictionaries
    """
    backups = []
    backup_root = Path(export_path) / "BACKUP"
    
    if not backup_root.exists():
        return backups
    
    try:
        # Structure: BACKUP/WorkspaceName/ModelName_operation_timestamp/
        for workspace_folder in backup_root.iterdir():
            if not workspace_folder.is_dir():
                continue
                
            workspace_name = workspace_folder.name
            
            for backup_folder in workspace_folder.iterdir():
                if not backup_folder.is_dir():
                    continue
                
                try:
                    # Parse folder name: ModelName_operation_YYYYMMDD_HHMMSS
                    # Example: "AdventureWorksDW19 With RLS CSV Report_migration_20251223_081051"
                    folder_name = backup_folder.name
                    
                    # Try to find timestamp pattern (YYYYMMDD_HHMMSS at the end)
                    import re
                    timestamp_pattern = r'(\d{8})_(\d{6})$'
                    match = re.search(timestamp_pattern, folder_name)
                    
                    if match:
                        date_str = match.group(1)
                        time_str = match.group(2)
                        timestamp_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                        
                        # Extract model name and operation (everything before the timestamp)
                        prefix = folder_name[:match.start()].rstrip('_')
                        parts = prefix.rsplit('_', 1)
                        
                        if len(parts) == 2:
                            model_name = parts[0]
                            operation = parts[1]
                        else:
                            model_name = prefix
                            operation = "backup"
                    else:
                        # Fallback: no valid timestamp found, try folder modification time
                        from datetime import datetime
                        try:
                            mtime = backup_folder.stat().st_mtime
                            timestamp_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            timestamp_str = "Unknown"
                        
                        # Try to extract model name from folder name
                        parts = folder_name.rsplit('_', 1)
                        if len(parts) == 2:
                            model_name = parts[0]
                            operation = parts[1]
                        else:
                            model_name = folder_name
                            operation = "backup"
                    
                    # Check what's backed up
                    has_semantic_model = False
                    has_report = False
                    
                    for item in backup_folder.iterdir():
                        if item.is_dir():
                            if (item / "definition" / "model.tmdl").exists():
                                has_semantic_model = True
                            if (item / "definition.pbir").exists():
                                has_report = True
                    
                    # Calculate size
                    total_size = sum(f.stat().st_size for f in backup_folder.rglob('*') if f.is_file())
                    size_mb = total_size / (1024 * 1024)
                    
                    backups.append({
                        'workspace': workspace_name,
                        'model_name': model_name,
                        'operation': operation,
                        'backup_path': str(backup_folder),
                        'timestamp': timestamp_str,
                        'has_semantic_model': has_semantic_model,
                        'has_report': has_report,
                        'size_mb': round(size_mb, 2)
                    })
                
                except Exception as e:
                    logger.warning(f"Error parsing backup folder {backup_folder}: {e}")
                    continue
    
    except Exception as e:
        logger.error(f"Error scanning backups: {e}")
    
    return backups


def get_latest_backup(model_path: str, operation_type: Optional[str] = None) -> Optional[Dict]:
    """
    Get the most recent backup for a specific model
    
    Args:
        model_path: Path to the model
        operation_type: Optional filter by operation type
    
    Returns: Backup dictionary or None
    """
    model_path = Path(model_path)
    export_root = _find_export_root(model_path)
    
    if not export_root:
        return None
    
    workspace_name, model_name = _extract_workspace_and_model(model_path)
    all_backups = scan_backups(str(export_root))
    
    # Filter backups for this specific model
    model_backups = [
        b for b in all_backups 
        if b['workspace'] == workspace_name and b['model_name'] == model_name
    ]
    
    # Further filter by operation type if specified
    if operation_type:
        model_backups = [b for b in model_backups if b['operation'] == operation_type]
    
    # Sort by timestamp (most recent first)
    model_backups.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return model_backups[0] if model_backups else None


def restore_from_backup(backup_path: str, destination_path: str) -> Tuple[bool, str]:
    """
    Restore a model from backup
    
    Args:
        backup_path: Path to the backup folder
        destination_path: Where to restore the model
    
    Returns: (success, message)
    """
    try:
        backup_path = Path(backup_path)
        destination_path = Path(destination_path)
        
        # Find the model folder inside the backup
        model_folders = [f for f in backup_path.iterdir() if f.is_dir()]
        
        if not model_folders:
            return False, "No model found in backup"
        
        model_backup = model_folders[0]
        
        # Remove existing destination if it exists
        if destination_path.exists():
            shutil.rmtree(destination_path)
        
        # Copy backup to destination
        shutil.copytree(model_backup, destination_path, dirs_exist_ok=True)
        
        logger.info(f"Restored from backup: {backup_path} -> {destination_path}")
        return True, f"Successfully restored from backup"
    
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        return False, f"Restore failed: {str(e)}"
