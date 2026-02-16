"""Folder management utilities for migration workflows."""

import shutil
from pathlib import Path
from typing import Optional
import json


def create_processed_data_folder(export_folder: Path) -> Path:
    """
    Create Processed_Data folder structure by copying from Raw Files.
    
    Args:
        export_folder: Path to FabricExport folder (e.g., FabricExport_2025-12-12_165401)
        
    Returns:
        Path to Processed_Data folder
        
    Raises:
        FileNotFoundError: If Raw Files folder doesn't exist
        Exception: If copy operation fails
    """
    raw_files = export_folder / "Raw Files"
    if not raw_files.exists():
        raise FileNotFoundError(f"Raw Files folder not found in {export_folder}")
    
    processed_data = export_folder / "Processed_Data"
    
    # If Processed_Data already exists, ask what to do
    if processed_data.exists():
        print(f"Processed_Data already exists: {processed_data}")
        return processed_data
    
    # Copy Raw Files to Processed_Data
    print(f"Creating Processed_Data folder from Raw Files...")
    shutil.copytree(raw_files, processed_data)
    print(f"✓ Processed_Data created: {processed_data}")
    
    return processed_data


def get_or_create_processed_folder(export_folder: Path, force_recreate: bool = False) -> Path:
    """
    Get existing Processed_Data folder or create it from Raw Files.
    
    Args:
        export_folder: Path to FabricExport folder
        force_recreate: If True, delete existing and recreate
        
    Returns:
        Path to Processed_Data folder
    """
    processed_data = export_folder / "Processed_Data"
    
    if force_recreate and processed_data.exists():
        print(f"Removing existing Processed_Data folder...")
        shutil.rmtree(processed_data)
    
    if not processed_data.exists():
        return create_processed_data_folder(export_folder)
    
    return processed_data


def find_item_in_processed_data(export_folder: Path, workspace_name: str, item_name: str) -> Optional[Path]:
    """
    Find a specific item in Processed_Data folder.
    
    Args:
        export_folder: Path to FabricExport folder
        workspace_name: Name of the workspace
        item_name: Full name of item (e.g., "Contoso.Report" or "Contoso.SemanticModel")
        
    Returns:
        Path to the item folder, or None if not found
    """
    processed_data = export_folder / "Processed_Data" / workspace_name / item_name
    
    if processed_data.exists() and processed_data.is_dir():
        return processed_data
    
    return None


def list_workspaces_in_processed_data(export_folder: Path) -> list[str]:
    """
    List all workspace folders in Processed_Data.
    
    Args:
        export_folder: Path to FabricExport folder
        
    Returns:
        List of workspace names
    """
    processed_data = export_folder / "Processed_Data"
    
    if not processed_data.exists():
        return []
    
    workspaces = []
    for item in processed_data.iterdir():
        if item.is_dir():
            workspaces.append(item.name)
    
    return sorted(workspaces)


def get_export_info(export_folder: Path) -> dict:
    """
    Get export information from workspaces_hierarchy.json.
    
    Args:
        export_folder: Path to FabricExport folder
        
    Returns:
        Dictionary with export metadata
    """
    json_file = export_folder / "workspaces_hierarchy.json"
    
    if not json_file.exists():
        return {}
    
    with open(json_file, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def ensure_processed_data_structure(export_folder: Path) -> tuple[Path, Path]:
    """
    Ensure both Raw Files and Processed_Data exist with proper structure.
    
    Args:
        export_folder: Path to FabricExport folder
        
    Returns:
        Tuple of (raw_files_path, processed_data_path)
        
    Raises:
        FileNotFoundError: If export folder or Raw Files doesn't exist
    """
    if not export_folder.exists():
        raise FileNotFoundError(f"Export folder not found: {export_folder}")
    
    raw_files = export_folder / "Raw Files"
    if not raw_files.exists():
        raise FileNotFoundError(f"Raw Files not found in {export_folder}")
    
    processed_data = get_or_create_processed_folder(export_folder)
    
    return raw_files, processed_data
