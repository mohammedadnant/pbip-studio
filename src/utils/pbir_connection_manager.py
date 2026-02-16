"""
PBIR Connection Manager Module
Manages definition.pbir connection strings for local development and Fabric publishing
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


def set_local_semantic_model_connection(report_path: str, semantic_model_name: str) -> Tuple[bool, str]:
    """
    Update report's definition.pbir to point to local semantic model
    
    Args:
        report_path: Path to the report folder (contains definition.pbir)
        semantic_model_name: Name of the semantic model (without extension)
    
    Returns: (success, message)
    """
    try:
        report_path = Path(report_path)
        pbir_file = report_path / "definition.pbir"
        
        if not pbir_file.exists():
            return False, f"definition.pbir not found in {report_path}"
        
        # Read current definition
        with open(pbir_file, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        # Set local connection (byPath reference with relative path)
        definition["datasetReference"] = {
            "byPath": {
                "path": f"../{semantic_model_name}.SemanticModel"
            }
        }
        
        # Write back
        with open(pbir_file, 'w', encoding='utf-8') as f:
            json.dump(definition, f, indent=4)
        
        logger.info(f"Set local connection: {report_path.name} -> {semantic_model_name}.SemanticModel")
        return True, f"Connected to local semantic model: {semantic_model_name}"
    
    except Exception as e:
        logger.error(f"Failed to set local connection: {str(e)}")
        return False, f"Failed to set local connection: {str(e)}"


def get_fabric_connection_from_backup(backup_path: str, report_name: str) -> Optional[Dict]:
    """
    Extract the original Fabric connection string from backup
    
    Args:
        backup_path: Path to the backup folder
        report_name: Name of the report folder
    
    Returns: Original connection dictionary or None
    """
    try:
        backup_path = Path(backup_path)
        
        # Find report folder in backup
        report_folders = list(backup_path.rglob(report_name))
        
        if not report_folders:
            logger.warning(f"Report {report_name} not found in backup")
            return None
        
        pbir_file = report_folders[0] / "definition.pbir"
        
        if not pbir_file.exists():
            logger.warning(f"definition.pbir not found for {report_name} in backup")
            return None
        
        # Read backup definition
        with open(pbir_file, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        if "datasetReference" in definition:
            return definition["datasetReference"]
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to get backup connection: {str(e)}")
        return None


def restore_fabric_connection_string(report_path: str, backup_path: str) -> Tuple[bool, str]:
    """
    Restore original Fabric connection string from backup
    
    Args:
        report_path: Path to the report folder
        backup_path: Path to the backup folder
    
    Returns: (success, message)
    """
    try:
        report_path = Path(report_path)
        report_name = report_path.name
        
        pbir_file = report_path / "definition.pbir"
        
        if not pbir_file.exists():
            return False, f"definition.pbir not found in {report_path}"
        
        # Get original connection from backup
        original_connection = get_fabric_connection_from_backup(backup_path, report_name)
        
        if not original_connection:
            logger.warning(f"Could not find backup connection for {report_name}, keeping current")
            return True, "No backup connection found (using current)"
        
        # Read current definition
        with open(pbir_file, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        # Restore original connection
        definition["datasetReference"] = original_connection
        
        # Write back
        with open(pbir_file, 'w', encoding='utf-8') as f:
            json.dump(definition, f, indent=4)
        
        logger.info(f"Restored Fabric connection for {report_name}")
        return True, "Restored Fabric connection from backup"
    
    except Exception as e:
        logger.error(f"Failed to restore connection: {str(e)}")
        return False, f"Failed to restore connection: {str(e)}"


def set_fabric_connection_string(
    report_path: str, 
    workspace_id: str, 
    semantic_model_id: str,
    semantic_model_name: str
) -> Tuple[bool, str]:
    """
    Set Fabric connection string for publishing
    
    Args:
        report_path: Path to the report folder
        workspace_id: Fabric workspace ID
        semantic_model_id: Fabric semantic model ID
        semantic_model_name: Name of the semantic model
    
    Returns: (success, message)
    """
    try:
        report_path = Path(report_path)
        pbir_file = report_path / "definition.pbir"
        
        if not pbir_file.exists():
            return False, f"definition.pbir not found in {report_path}"
        
        # Read current definition
        with open(pbir_file, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        # Build Fabric connection string
        connection_string = (
            f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_id};"
            f"Initial Catalog={semantic_model_name};"
            f"Integrated Security=ClaimsToken;"
            f"semanticmodelid={semantic_model_id}"
        )
        
        # Set Fabric connection
        definition["datasetReference"] = {
            "byConnection": {
                "connectionString": connection_string
            }
        }
        
        # Write back
        with open(pbir_file, 'w', encoding='utf-8') as f:
            json.dump(definition, f, indent=4)
        
        logger.info(f"Set Fabric connection for {report_path.name}")
        return True, "Set Fabric connection string"
    
    except Exception as e:
        logger.error(f"Failed to set Fabric connection: {str(e)}")
        return False, f"Failed to set Fabric connection: {str(e)}"


def get_current_connection_type(report_path: str) -> Optional[str]:
    """
    Determine current connection type (local or fabric)
    
    Args:
        report_path: Path to the report folder
    
    Returns: "local", "fabric", or None
    """
    try:
        report_path = Path(report_path)
        pbir_file = report_path / "definition.pbir"
        
        if not pbir_file.exists():
            return None
        
        with open(pbir_file, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        if "datasetReference" not in definition:
            return None
        
        ref = definition["datasetReference"]
        
        if "byPath" in ref:
            return "local"
        elif "byConnection" in ref:
            return "fabric"
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to determine connection type: {str(e)}")
        return None


def find_related_reports(model_path: str) -> list[Path]:
    """
    Find all reports in the same workspace that might reference this semantic model
    
    Args:
        model_path: Path to the semantic model
    
    Returns: List of report folder paths
    """
    try:
        model_path = Path(model_path)
        
        # Get workspace folder (parent of model)
        workspace_folder = model_path.parent
        
        # Find all .Report folders in the workspace
        reports = []
        for item in workspace_folder.iterdir():
            if item.is_dir() and item.name.endswith(".Report"):
                if (item / "definition.pbir").exists():
                    reports.append(item)
        
        return reports
    
    except Exception as e:
        logger.error(f"Failed to find related reports: {str(e)}")
        return []


def set_all_reports_to_local(model_path: str) -> Tuple[int, int]:
    """
    Set all reports in the workspace to point to local semantic model
    ONLY updates reports that originally referenced this specific semantic model
    
    Args:
        model_path: Path to the semantic model
    
    Returns: (success_count, error_count)
    """
    model_path = Path(model_path)
    # Remove .SemanticModel extension from the name
    semantic_model_name = model_path.name.replace('.SemanticModel', '')
    
    reports = find_related_reports(str(model_path))
    success_count = 0
    error_count = 0
    
    for report in reports:
        # Check if this report originally referenced this semantic model
        if _report_references_model(report, semantic_model_name):
            success, _ = set_local_semantic_model_connection(str(report), semantic_model_name)
            if success:
                success_count += 1
            else:
                error_count += 1
        else:
            logger.debug(f"Skipping {report.name} - does not reference {semantic_model_name}")
    
    return success_count, error_count


def _report_references_model(report_path: Path, semantic_model_name: str) -> bool:
    """
    Check if a report references the specified semantic model
    
    Args:
        report_path: Path to the report folder
        semantic_model_name: Name of the semantic model to check
    
    Returns: True if report references this model
    """
    try:
        pbir_file = report_path / "definition.pbir"
        
        if not pbir_file.exists():
            return False
        
        with open(pbir_file, 'r', encoding='utf-8') as f:
            definition = json.load(f)
        
        if "datasetReference" not in definition:
            return False
        
        ref = definition["datasetReference"]
        
        # Check byPath reference (local)
        if "byPath" in ref:
            path = ref["byPath"].get("path", "")
            # Extract model name from path like "../ModelName.SemanticModel"
            if semantic_model_name in path:
                return True
        
        # Check byConnection reference (Fabric)
        if "byConnection" in ref:
            connection_string = ref["byConnection"].get("connectionString", "")
            # Extract Initial Catalog value which contains the semantic model name
            # Format: "initial catalog=\"ModelName\""
            import re
            match = re.search(r'initial\s+catalog\s*=\s*["\']?([^";]+)["\']?', connection_string, re.IGNORECASE)
            if match:
                catalog_name = match.group(1).strip('"').strip("'")
                if catalog_name == semantic_model_name:
                    return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking report reference: {str(e)}")
        return False
