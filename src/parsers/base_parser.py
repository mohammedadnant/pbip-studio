"""Base parser interface for BI tool metadata extraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from models import Workspace, Dataset, DataObject, DataSource


class BaseParser(ABC):
    """Abstract base class for BI tool parsers."""
    
    def __init__(self, tool_id: str):
        """
        Initialize parser.
        
        Args:
            tool_id: Identifier for the BI tool (e.g., 'powerbi', 'tableau')
        """
        self.tool_id = tool_id
        
    @abstractmethod
    def parse_workspace(self, path: Path) -> Workspace:
        """
        Parse workspace/project from path.
        
        Args:
            path: Path to workspace directory
            
        Returns:
            Workspace object
        """
        pass
        
    @abstractmethod
    def parse_dataset(self, path: Path, workspace_id: str) -> Dataset:
        """
        Parse dataset/workbook from path.
        
        Args:
            path: Path to dataset directory
            workspace_id: Parent workspace ID
            
        Returns:
            Dataset object
        """
        pass
        
    @abstractmethod
    def parse_data_objects(self, dataset_path: Path, dataset_id: str) -> List[DataObject]:
        """
        Parse data objects (tables/sheets) from dataset.
        
        Args:
            dataset_path: Path to dataset directory
            dataset_id: Parent dataset ID
            
        Returns:
            List of DataObject instances
        """
        pass
        
    @abstractmethod
    def parse_data_sources(self, data_object_path: Path, object_id: int) -> List[DataSource]:
        """
        Parse data sources from data object.
        
        Args:
            data_object_path: Path to data object file
            object_id: Parent data object ID
            
        Returns:
            List of DataSource instances
        """
        pass
        
    @abstractmethod
    def detect_migration_needs(self, data_source: DataSource) -> bool:
        """
        Determine if data source requires migration.
        
        Args:
            data_source: DataSource to evaluate
            
        Returns:
            True if migration is needed
        """
        pass
        
    def parse_hierarchy(self, root_path: Path) -> Dict:
        """
        Parse entire hierarchy from root path.
        
        Args:
            root_path: Root directory containing workspaces/datasets
            
        Returns:
            Dictionary with parsed hierarchy
        """
        result = {
            'workspaces': [],
            'datasets': [],
            'data_objects': [],
            'data_sources': []
        }
        
        # Override in subclass for specific tool structure
        return result
