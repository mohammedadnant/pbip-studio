"""
Microsoft Fabric REST API Wrapper
Pure Python implementation using Fabric REST API directly

This module provides a programmatic interface to Microsoft Fabric
for downloading Power BI and Fabric workspace items.

Key Features:
    - No PowerShell dependencies
    - Direct REST API calls
    - Support for both interactive and service principal auth
    - Download semantic models, reports, and other items as PBIP/TMDL
    - Cross-platform support (Windows, Linux, Mac)

Usage:
    from src.services.fabric_cli_wrapper import FabricCLIWrapper
    
    # Initialize and authenticate
    client = FabricCLIWrapper()
    client.login()  # Interactive browser auth
    
    # Or use service principal
    client = FabricCLIWrapper(
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-secret"
    )
    client.login()
    
    # List workspaces
    workspaces = client.list_workspaces()
    
    # Download items
    client.download_item(
        workspace_id="ws-id",
        item_id="item-id",
        item_type="SemanticModel",
        local_path="./downloads/model.pbip"
    )
"""

import logging
import os
import requests
import json
import base64
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def load_config_from_file(config_path: str = "config.md") -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Load Azure AD credentials from config.md file
    
    Args:
        config_path: Path to config.md file (relative to project root)
    
    Returns:
        Tuple of (tenant_id, client_id, client_secret)
    """
    try:
        # Try to find config.md in common locations
        possible_paths = [
            Path(config_path),
            Path.cwd() / config_path,
            Path(__file__).parent.parent.parent / config_path,
        ]
        
        config_file = None
        for path in possible_paths:
            if path.exists():
                config_file = path
                break
        
        if not config_file:
            logger.warning(f"Config file not found at any location: {config_path}")
            return None, None, None
        
        content = config_file.read_text()
        
        # Parse credentials from config.md
        tenant_match = re.search(r'tenantId\s*=\s*["\']([^"\']+)["\']', content)
        client_match = re.search(r'clientId\s*=\s*["\']([^"\']+)["\']', content)
        secret_match = re.search(r'clientSecret\s*=\s*["\']([^"\']+)["\']', content)
        
        tenant_id = tenant_match.group(1) if tenant_match else None
        client_id = client_match.group(1) if client_match else None
        client_secret = secret_match.group(1) if secret_match else None
        
        if tenant_id and client_id and client_secret:
            logger.info(f"✓ Loaded credentials from {config_file}")
            return tenant_id, client_id, client_secret
        else:
            logger.warning(f"Incomplete credentials in {config_file}")
            return None, None, None
            
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None, None, None


@dataclass
class FabricItem:
    """Represents a Fabric workspace item"""
    id: str
    name: str
    type: str
    workspace_id: str
    description: Optional[str] = None
    

class FabricCLIWrapper:
    """
    Wrapper for Microsoft Fabric REST API
    
    Provides programmatic access to Fabric workspaces without
    requiring PowerShell or external CLI tools.
    """
    
    BASE_URL = "https://api.fabric.microsoft.com/v1"
    SCOPE = "https://analysis.windows.net/powerbi/api/.default"
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        use_environment_vars: bool = True,
        use_config_file: bool = True
    ):
        """
        Initialize Fabric REST API wrapper
        
        Args:
            tenant_id: Azure AD tenant ID (optional, can use env var or config.md)
            client_id: Service principal client ID (optional, can use env var or config.md)
            client_secret: Service principal secret (optional, can use env var or config.md)
            use_environment_vars: Load credentials from environment if not provided
            use_config_file: Load credentials from config.md if not provided
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.credential = None
        self.access_token = None
        self.authenticated = False
        self.session = requests.Session()
        
        # Priority: 1. Parameters, 2. config.md, 3. Environment variables
        
        # Try to load from config.md first if enabled
        if use_config_file and not all([self.tenant_id, self.client_id, self.client_secret]):
            config_tenant, config_client, config_secret = load_config_from_file()
            self.tenant_id = self.tenant_id or config_tenant
            self.client_id = self.client_id or config_client
            self.client_secret = self.client_secret or config_secret
        
        # Then load from environment if requested and still not provided
        if use_environment_vars and not all([self.tenant_id, self.client_id, self.client_secret]):
            self.tenant_id = self.tenant_id or os.getenv('AZURE_TENANT_ID')
            self.client_id = self.client_id or os.getenv('AZURE_CLIENT_ID')
            self.client_secret = self.client_secret or os.getenv('AZURE_CLIENT_SECRET')
    
    def login(self, interactive: bool = None) -> bool:
        """
        Authenticate to Microsoft Fabric
        
        Args:
            interactive: If True, use browser auth. If False, use service principal.
                        If None, auto-detect based on credentials availability.
        
        Returns:
            True if authentication successful
            
        Raises:
            ImportError: If required packages are not installed
            Exception: If authentication fails
        """
        try:
            # Import Azure authentication libraries
            from azure.identity import InteractiveBrowserCredential, ClientSecretCredential
            
            logger.info("Initializing Microsoft Fabric authentication...")
            
            # Determine auth method
            if interactive is None:
                # Auto-detect: use service principal if credentials are available
                interactive = not all([self.tenant_id, self.client_id, self.client_secret])
            
            if interactive:
                logger.info("Using interactive browser authentication...")
                self.credential = InteractiveBrowserCredential()
            else:
                logger.info("Using service principal authentication...")
                if not all([self.tenant_id, self.client_id, self.client_secret]):
                    raise ValueError("Tenant ID, Client ID, and Client Secret are required for service principal auth")
                
                self.credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            
            # Get access token
            token = self.credential.get_token(self.SCOPE)
            self.access_token = token.token
            
            # Set session headers
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            })
            
            self.authenticated = True
            logger.info("✓ Successfully authenticated to Microsoft Fabric")
            return True
            
        except ImportError as e:
            error_msg = f"Required package not found: {e}\nInstall with: pip install azure-identity"
            logger.error(error_msg)
            raise ImportError(error_msg)
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.authenticated = False
            raise
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        List all accessible Fabric workspaces
        
        Returns:
            List of workspace dictionaries with id, name, description, etc.
            
        Raises:
            RuntimeError: If not authenticated
        """
        self._ensure_authenticated()
        
        try:
            logger.info("Fetching Fabric workspaces...")
            response = self.session.get(f"{self.BASE_URL}/workspaces")
            response.raise_for_status()
            
            data = response.json()
            workspaces = data.get('value', [])
            logger.info(f"Found {len(workspaces)} workspaces")
            return workspaces
            
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            raise
    
    def list_workspace_items(
        self,
        workspace_id: str,
        item_type: Optional[str] = None
    ) -> List[FabricItem]:
        """
        List items in a specific workspace
        
        Args:
            workspace_id: Fabric workspace ID
            item_type: Filter by item type (e.g., 'SemanticModel', 'Report')
                      If None, returns all items
        
        Returns:
            List of FabricItem objects
            
        Raises:
            RuntimeError: If not authenticated
        """
        self._ensure_authenticated()
        
        try:
            logger.info(f"Listing items in workspace {workspace_id}...")
            response = self.session.get(f"{self.BASE_URL}/workspaces/{workspace_id}/items")
            response.raise_for_status()
            
            data = response.json()
            items_raw = data.get('value', [])
            
            items = []
            for item_data in items_raw:
                # Filter by type if specified
                if item_type and item_data.get('type') != item_type:
                    continue
                
                item = FabricItem(
                    id=item_data['id'],
                    name=item_data['displayName'],
                    type=item_data['type'],
                    workspace_id=workspace_id,
                    description=item_data.get('description')
                )
                items.append(item)
            
            logger.info(f"Found {len(items)} items" + (f" of type {item_type}" if item_type else ""))
            return items
            
        except Exception as e:
            logger.error(f"Failed to list workspace items: {e}")
            raise
    
    def download_item(
        self,
        workspace_id: str,
        item_id: str,
        item_type: str,
        local_path: str,
        format: str = "PBIP"
    ) -> Path:
        """
        Download a Fabric item to local storage
        
        Args:
            workspace_id: Fabric workspace ID
            item_id: Item ID to download
            item_type: Item type ('SemanticModel', 'Report', etc.)
            local_path: Local path to save the item
            format: Download format ('PBIP' or 'TMDL')
        
        Returns:
            Path to the downloaded file/directory
            
        Raises:
            RuntimeError: If not authenticated
            ValueError: If invalid parameters
        """
        self._ensure_authenticated()
        
        # Validate inputs
        valid_types = ['SemanticModel', 'Report', 'Dashboard', 'Dataflow', 'Lakehouse']
        if item_type not in valid_types:
            raise ValueError(f"Item type must be one of: {valid_types}")
        
        valid_formats = ['PBIP', 'TMDL']
        if format.upper() not in valid_formats:
            raise ValueError(f"Format must be one of: {valid_formats}")
        
        try:
            logger.info(f"Downloading {item_type} {item_id} from workspace {workspace_id}...")
            logger.info(f"Format: {format}, Destination: {local_path}")
            
            # Create parent directory if it doesn't exist
            local_path_obj = Path(local_path)
            local_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Initiate the download operation (returns 202 Accepted)
            logger.info(f"Initiating download request to API...")
            response = self.session.post(
                f"{self.BASE_URL}/workspaces/{workspace_id}/items/{item_id}/getDefinition",
                json={"format": format.upper()}
            )
            
            logger.info(f"API response status: {response.status_code}")
            
            if response.status_code == 202:
                # Async operation - need to poll for completion
                operation_url = response.headers.get('Location')
                retry_after = int(response.headers.get('Retry-After', 5))
                
                logger.info(f"Async operation started. Polling every {retry_after} seconds...")
                logger.info(f"Operation URL: {operation_url}")
                
                # Step 2: Poll the operation status
                import time
                max_attempts = 60  # 5 minutes max
                attempt = 0
                
                while attempt < max_attempts:
                    attempt += 1
                    time.sleep(retry_after)
                    
                    status_response = self.session.get(operation_url)
                    status_response.raise_for_status()
                    
                    status_data = status_response.json()
                    status = status_data.get('status', 'Unknown')
                    
                    logger.info(f"Attempt {attempt}: Status = {status}")
                    
                    if status == 'Succeeded':
                        # Operation completed successfully
                        # Now get the actual result from the result endpoint
                        logger.info("Operation completed. Retrieving result...")
                        result_url = f"{operation_url}/result"
                        result_response = self.session.get(result_url)
                        result_response.raise_for_status()
                        definition_data = result_response.json()
                        logger.info(f"Retrieved result with keys: {list(definition_data.keys()) if isinstance(definition_data, dict) else type(definition_data)}")
                        break
                    elif status in ['Failed', 'Cancelled']:
                        error = status_data.get('error', {})
                        error_msg = error.get('message', 'Unknown error')
                        raise RuntimeError(f"Operation {status}: {error_msg}")
                    elif status in ['Running', 'NotStarted']:
                        # Continue polling
                        continue
                    else:
                        logger.warning(f"Unknown status: {status}")
                        continue
                else:
                    raise TimeoutError("Operation timed out after 5 minutes")
                    
            else:
                # Synchronous response (unlikely but handle it)
                response.raise_for_status()
                definition_data = response.json()
            
            logger.info(f"Definition data keys: {list(definition_data.keys()) if isinstance(definition_data, dict) else 'Not a dict'}")
            
            # Check if definition_data is None or empty
            if not definition_data:
                raise ValueError("Empty response from Fabric API")
            
            # Handle the response structure - it may be 'definition' or direct content
            definition = definition_data.get('definition')
            if not definition:
                # Sometimes the response is the definition itself
                definition = definition_data
            
            # Extract and save files
            parts = definition.get('parts', [])
            if not parts:
                logger.warning("No parts found in definition")
                # Save the raw response as JSON for debugging
                debug_path = local_path_obj.parent / f"{local_path_obj.stem}_debug.json"
                debug_path.write_text(json.dumps(definition_data, indent=2))
                raise ValueError(f"No parts found in definition. Debug info saved to {debug_path}")
            
            logger.info(f"Found {len(parts)} parts to download")
            
            for part in parts:
                part_path = local_path_obj / part['path']
                part_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Decode base64 payload if present
                if 'payload' in part:
                    content = base64.b64decode(part['payload'])
                    part_path.write_bytes(content)
                    logger.info(f"  Saved: {part['path']} ({len(content)} bytes)")
                elif 'payloadType' in part:
                    # Handle different payload types
                    part_path.write_text(json.dumps(part, indent=2))
                    logger.info(f"  Saved: {part['path']} (metadata)")
            
            logger.info(f"✓ Successfully downloaded to {local_path}")
            return local_path_obj
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}", exc_info=True)
            logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.error(f"Response text: {getattr(e.response, 'text', 'N/A')}")
            raise RuntimeError(f"Failed to download item: API request error - {str(e)}")
        except TimeoutError as e:
            logger.error(f"Download operation timed out: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to download item: {e}", exc_info=True)
            raise RuntimeError(f"Failed to download item: {str(e)}")
    
    def download_semantic_model(
        self,
        workspace_id: str,
        model_id: str,
        local_path: str,
        format: str = "TMDL"
    ) -> Path:
        """
        Convenience method to download a semantic model
        
        Args:
            workspace_id: Fabric workspace ID
            model_id: Semantic model ID
            local_path: Local path to save
            format: 'TMDL' or 'PBIP' (default: TMDL)
        
        Returns:
            Path to downloaded model
        """
        return self.download_item(
            workspace_id=workspace_id,
            item_id=model_id,
            item_type="SemanticModel",
            local_path=local_path,
            format=format
        )
    
    def download_report(
        self,
        workspace_id: str,
        report_id: str,
        local_path: str
    ) -> Path:
        """
        Convenience method to download a Power BI report
        
        Args:
            workspace_id: Fabric workspace ID
            report_id: Report ID
            local_path: Local path to save
        
        Returns:
            Path to downloaded report
        """
        return self.download_item(
            workspace_id=workspace_id,
            item_id=report_id,
            item_type="Report",
            local_path=local_path,
            format="PBIP"
        )
    
    def upload_item(
        self,
        workspace_id: str,
        local_path: str,
        item_type: str,
        item_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a local item to Fabric workspace
        
        Args:
            workspace_id: Target Fabric workspace ID
            local_path: Path to local PBIP/TMDL file/folder
            item_type: Item type ('SemanticModel', 'Report', etc.)
            item_name: Optional name for the item (defaults to filename)
        
        Returns:
            Dictionary with upload result including item ID
            
        Raises:
            RuntimeError: If not authenticated
            NotImplementedError: Upload functionality requires Power BI REST API
        """
        raise NotImplementedError(
            "Upload functionality is not yet implemented in this version. "
            "Please use the existing FabricClient for upload operations."
        )
    
    def get_item_definition(
        self,
        workspace_id: str,
        item_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed definition of a Fabric item
        
        Args:
            workspace_id: Fabric workspace ID
            item_id: Item ID
        
        Returns:
            Dictionary with item definition details
        """
        self._ensure_authenticated()
        
        try:
            logger.info(f"Getting definition for item {item_id}...")
            response = self.session.post(
                f"{self.BASE_URL}/workspaces/{workspace_id}/items/{item_id}/getDefinition"
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get item definition: {e}")
            raise
    
    def _ensure_authenticated(self):
        """Verify authentication status"""
        if not self.authenticated or self.credential is None:
            raise RuntimeError(
                "Not authenticated. Call login() first to authenticate."
            )
        if not self.session or not self.access_token:
            raise RuntimeError(
                "Session is not properly initialized. Please re-authenticate."
            )
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Cleanup if needed
        if self.session:
            self.session.close()
        self.credential = None
        self.authenticated = False
