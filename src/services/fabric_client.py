"""
Microsoft Fabric REST API Client
Replaces PowerShell/Fabric CLI with direct Python implementation

IMPORTANT: This client is for MICROSOFT FABRIC workspaces only!

For Power BI Service workspaces, use PowerBIDownloader instead:
    - Power BI REST API does NOT support PBIP/TMDL download
    - Only PBIX format is available via Power BI REST API
    - Use PowerBIDownloader with XMLA endpoint for TMDL export

Use this FabricClient when:
    ✅ Working with Microsoft Fabric workspaces
    ✅ Items are already in Fabric (not classic Power BI)
    ✅ Need to download/upload PBIP/TMDL format

Use PowerBIDownloader when:
    ⚠️ Working with classic Power BI Service
    ⚠️ Need TMDL format from Power BI datasets
    ⚠️ Have Premium/Fabric capacity with XMLA enabled
"""

import json
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import requests
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError


logger = logging.getLogger(__name__)


@dataclass
class FabricConfig:
    """Fabric authentication configuration"""
    tenant_id: str
    client_id: str
    client_secret: str


class FabricAPIError(Exception):
    """Custom exception for Fabric API errors"""
    pass


class FabricClient:
    """
    Client for Microsoft Fabric REST API
    
    Download and upload items in PBIP/TMDL format from Microsoft Fabric workspaces.
    
    Note: This does NOT work with classic Power BI Service workspaces.
    For Power BI Service, use PowerBIDownloader with XMLA endpoint instead.
    """
    
    BASE_URL = "https://api.fabric.microsoft.com/v1"
    POWERBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
    
    def __init__(self, config: FabricConfig):
        """
        Initialize Fabric client with service principal credentials
        
        Args:
            config: FabricConfig with tenant_id, client_id, client_secret
        """
        self.config = config
        self.credential = None
        self.access_token = None
        self._session = requests.Session()
        
    def authenticate(self) -> bool:
        """
        Authenticate using service principal (client credentials)
        
        Returns:
            True if authentication successful
            
        Raises:
            FabricAPIError if authentication fails
        """
        try:
            logger.info("Authenticating to Microsoft Fabric...")
            
            self.credential = ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret
            )
            
            # Get access token
            token = self.credential.get_token(self.POWERBI_SCOPE)
            self.access_token = token.token
            
            # Set default headers
            self._session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            })
            
            logger.info("Authentication successful")
            return True
            
        except ClientAuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise FabricAPIError(f"Authentication failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise FabricAPIError(f"Authentication error: {str(e)}")
    
    def _refresh_token_if_needed(self):
        """Refresh access token if expired"""
        if self.credential:
            token = self.credential.get_token(self.POWERBI_SCOPE)
            if token.token != self.access_token:
                self.access_token = token.token
                self._session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request to Fabric API with error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (will be appended to BASE_URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            FabricAPIError on API errors
        """
        self._refresh_token_if_needed()
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = self._session.request(method, url, **kwargs)
            
            # Log request details
            logger.debug(f"{method} {url} - Status: {response.status_code}")
            
            # Raise for HTTP errors (but allow 202 Accepted for async operations)
            if response.status_code >= 400:
                error_msg = f"API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise FabricAPIError(error_msg)
            
            # Log if we got 202 (async operation)
            if response.status_code == 202:
                logger.info(f"Received 202 Accepted - async operation initiated")
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise FabricAPIError(f"Request failed: {str(e)}")
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        List all workspaces accessible to the authenticated user
        
        Returns:
            List of workspace dictionaries with id, name, type, etc.
        """
        logger.info("Fetching workspaces...")
        
        response = self._make_request("GET", "/workspaces")
        data = response.json()
        
        workspaces = data.get("value", [])
        logger.info(f"Found {len(workspaces)} workspaces")
        
        return workspaces
    
    def get_workspace_items(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get all items (reports, datasets, etc.) in a workspace
        
        Args:
            workspace_id: Workspace GUID
            
        Returns:
            List of item dictionaries
        """
        logger.info(f"Fetching items from workspace {workspace_id}...")
        
        response = self._make_request("GET", f"/workspaces/{workspace_id}/items")
        data = response.json()
        
        items = data.get("value", [])
        logger.info(f"Found {len(items)} items")
        
        return items
    
    def get_item_definition(
        self, 
        workspace_id: str, 
        item_id: str,
        format: str = "TMDL",
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Get item definition (PBIP format) - handles long-running operations
        
        Args:
            workspace_id: Workspace GUID
            item_id: Item GUID
            format: Definition format - "TMDL" or "TMSL" (default: TMDL)
            timeout: Max wait time in seconds for LRO completion (default: 300)
            
        Returns:
            Dictionary with definition parts (files)
        """
        import time
        
        logger.info(f"Fetching definition for item {item_id} in format {format}...")
        
        # POST to get definition
        payload = {"format": format}
        response = self._make_request(
            "POST",
            f"/workspaces/{workspace_id}/items/{item_id}/getDefinition",
            json=payload
        )
        
        # Check if this is a long-running operation (LRO)
        if response.status_code == 202:
            # Get operation location from headers
            operation_url = response.headers.get("Location") or response.headers.get("Azure-AsyncOperation")
            
            if not operation_url:
                logger.error("Got 202 but no Location header for polling")
                return {"definition": {"parts": []}}
            
            logger.info(f"Long-running operation started")
            logger.debug(f"Operation URL: {operation_url}")
            
            # Poll for completion
            start_time = time.time()
            retry_after = int(response.headers.get("Retry-After", 5))
            
            while time.time() - start_time < timeout:
                time.sleep(retry_after)
                
                # Poll the operation status
                poll_response = self._session.get(
                    operation_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if poll_response.status_code == 200:
                    # Check if operation completed
                    try:
                        status_response = poll_response.json()
                        operation_status = status_response.get("status", "")
                        
                        logger.debug(f"Operation status: {operation_status}, percent: {status_response.get('percentComplete', 0)}%")
                        
                        if operation_status == "Succeeded":
                            # Operation completed successfully
                            logger.info(f"Operation succeeded!")
                            
                            # Check if definition is in the status response
                            if "definition" in status_response:
                                logger.info(f"✓ Definition retrieved from status response")
                                return status_response
                            
                            # The result should be available at a result endpoint
                            # Typically it's the operation URL with /result appended
                            # Or check the operationResultUrl in the response
                            result_url = status_response.get("operationResultUrl")
                            if not result_url:
                                # Try appending /result to operation URL
                                if "/operations/" in operation_url:
                                    result_url = f"{operation_url}/result"
                                else:
                                    logger.error("Cannot determine result URL")
                                    return {"definition": {"parts": []}}
                            
                            logger.debug(f"Fetching result from: {result_url}")
                            
                            # Fetch the actual result
                            result_response = self._session.get(
                                result_url,
                                headers={"Authorization": f"Bearer {self.access_token}"}
                            )
                            
                            if result_response.status_code == 200 and result_response.content:
                                try:
                                    result = result_response.json()
                                    logger.info(f"✓ Definition retrieved successfully")
                                    return result
                                except Exception as e:
                                    logger.error(f"Failed to parse result: {e}")
                                    return {"definition": {"parts": []}}
                            else:
                                logger.error(f"Failed to fetch result: HTTP {result_response.status_code}")
                                logger.error(f"Response: {result_response.text[:200]}")
                                return {"definition": {"parts": []}}
                        
                        elif operation_status == "Failed":
                            error_msg = status_response.get("error", {}).get("message", "Unknown error")
                            logger.error(f"Operation failed: {error_msg}")
                            return {"definition": {"parts": []}}
                        
                        elif operation_status in ["NotStarted", "Running", "Undefined"]:
                            # Still in progress
                            logger.debug(f"Operation still in progress...")
                            retry_after = int(poll_response.headers.get("Retry-After", retry_after))
                            continue
                        
                        else:
                            logger.warning(f"Unknown operation status: {operation_status}")
                            continue
                            
                    except Exception as e:
                        logger.error(f"Failed to parse operation status response: {e}")
                        return {"definition": {"parts": []}}
                
                elif poll_response.status_code == 202:
                    # Still in progress
                    logger.debug(f"Operation still in progress (202), retrying in {retry_after}s...")
                    retry_after = int(poll_response.headers.get("Retry-After", retry_after))
                    continue
                
                else:
                    logger.error(f"Polling failed with status {poll_response.status_code}")
                    return {"definition": {"parts": []}}
            
            logger.error(f"Operation timed out after {timeout} seconds")
            return {"definition": {"parts": []}}
        
        # Immediate response (200)
        if not response.content:
            logger.warning(f"Empty response from getDefinition API for item {item_id}")
            return {"definition": {"parts": []}}
        
        try:
            definition = response.json()
            
            # Log what we actually received
            logger.debug(f"Received definition response: {definition}")
            
            if not definition:
                logger.warning(f"Null definition returned for item {item_id}")
                return {"definition": {"parts": []}}
            
            # Check if definition has the expected structure
            if "definition" not in definition:
                logger.warning(f"Definition response missing 'definition' key for item {item_id}. Keys present: {list(definition.keys())}")
                return {"definition": {"parts": []}}
            
            if "parts" not in definition.get("definition", {}):
                logger.warning(f"Definition missing 'parts' for item {item_id}")
                return {"definition": {"parts": []}}
            
            return definition
            
        except Exception as e:
            logger.error(f"Failed to parse definition response for item {item_id}: {e}")
            logger.error(f"Response content: {response.text[:500]}")  # Log first 500 chars
            return {"definition": {"parts": []}}
    
    def download_item(
        self,
        workspace_id: str,
        workspace_name: str,
        item: Dict[str, Any],
        output_dir: Path
    ) -> Tuple[bool, str]:
        """
        Download a single item (report or dataset) as PBIP
        
        Args:
            workspace_id: Workspace GUID
            workspace_name: Workspace name (for folder structure)
            item: Item dictionary from get_workspace_items
            output_dir: Base output directory
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        item_id = item["id"]
        item_name = item["displayName"]
        item_type = item["type"]
        
        logger.info(f"Downloading {item_type}: {item_name}")
        
        try:
            # Create folder structure: output_dir/workspace_name/item_name.ItemType/
            workspace_dir = output_dir / workspace_name
            
            # Clean item name for filesystem
            safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '-', '_')).strip()
            item_dir = workspace_dir / f"{safe_name}.{item_type}"
            item_dir.mkdir(parents=True, exist_ok=True)
            
            # Get item definition
            definition = self.get_item_definition(workspace_id, item_id)
            
            # Check if definition is valid
            if not definition or not isinstance(definition, dict):
                return False, f"No valid definition returned for {item_name}"
            
            # Extract definition parts
            parts = definition.get("definition", {}).get("parts", [])
            
            if not parts:
                return False, f"No definition parts found for {item_name}"
            
            # Write each part to file
            for part in parts:
                path = part.get("path", "")
                payload = part.get("payload", "")
                payload_type = part.get("payloadType", "InlineBase64")
                
                if not path:
                    continue
                
                # Create subdirectories if needed
                file_path = item_dir / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Decode and write payload
                if payload_type == "InlineBase64":
                    content = base64.b64decode(payload)
                    file_path.write_bytes(content)
                else:
                    # Assume text
                    file_path.write_text(payload, encoding='utf-8')
                
                logger.debug(f"  Wrote: {file_path.relative_to(output_dir)}")
            
            logger.info(f"✓ Downloaded {item_name} ({len(parts)} files)")
            return True, f"Downloaded {item_name}"
            
        except Exception as e:
            error_msg = f"Failed to download {item_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def download_workspace(
        self,
        workspace_id: str,
        workspace_name: str,
        output_dir: Path,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Download entire workspace (all reports and datasets)
        
        Args:
            workspace_id: Workspace GUID
            workspace_name: Workspace name
            output_dir: Base output directory
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            Dictionary with success/error counts and messages
        """
        logger.info(f"Downloading workspace: {workspace_name}")
        
        results = {
            "workspace_name": workspace_name,
            "success_count": 0,
            "error_count": 0,
            "messages": []
        }
        
        try:
            # Get all items in workspace
            items = self.get_workspace_items(workspace_id)
            total_items = len(items)
            
            if total_items == 0:
                msg = f"No items found in workspace {workspace_name}"
                logger.warning(msg)
                results["messages"].append(msg)
                return results
            
            logger.info(f"Found {total_items} items to download")
            
            # Download each item
            for idx, item in enumerate(items, 1):
                if progress_callback:
                    progress_callback(idx, total_items, f"Downloading {item['displayName']}")
                
                success, message = self.download_item(
                    workspace_id,
                    workspace_name,
                    item,
                    output_dir
                )
                
                if success:
                    results["success_count"] += 1
                else:
                    results["error_count"] += 1
                
                results["messages"].append(message)
            
            logger.info(
                f"Workspace download complete: "
                f"{results['success_count']} succeeded, "
                f"{results['error_count']} failed"
            )
            
        except Exception as e:
            error_msg = f"Failed to download workspace {workspace_name}: {str(e)}"
            logger.error(error_msg)
            results["messages"].append(error_msg)
            results["error_count"] += 1
        
        return results
    
    def download_all_workspaces(
        self,
        output_dir: Path,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Download all accessible workspaces
        
        Args:
            output_dir: Base output directory
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            Dictionary with overall statistics
        """
        logger.info("Starting download of all workspaces...")
        
        overall_results = {
            "total_workspaces": 0,
            "total_items_success": 0,
            "total_items_error": 0,
            "workspace_results": []
        }
        
        try:
            # Get all workspaces
            workspaces = self.list_workspaces()
            overall_results["total_workspaces"] = len(workspaces)
            
            if len(workspaces) == 0:
                logger.warning("No workspaces found")
                return overall_results
            
            # Download each workspace
            for ws_idx, workspace in enumerate(workspaces, 1):
                ws_name = workspace.get("displayName", workspace.get("name", "Unknown"))
                ws_id = workspace["id"]
                
                logger.info(f"\n[{ws_idx}/{len(workspaces)}] Processing workspace: {ws_name}")
                
                ws_results = self.download_workspace(
                    ws_id,
                    ws_name,
                    output_dir,
                    progress_callback
                )
                
                overall_results["total_items_success"] += ws_results["success_count"]
                overall_results["total_items_error"] += ws_results["error_count"]
                overall_results["workspace_results"].append(ws_results)
            
            logger.info(
                f"\n✓ All workspaces downloaded!\n"
                f"  Workspaces: {overall_results['total_workspaces']}\n"
                f"  Items succeeded: {overall_results['total_items_success']}\n"
                f"  Items failed: {overall_results['total_items_error']}"
            )
            
        except Exception as e:
            error_msg = f"Failed during workspace download: {str(e)}"
            logger.error(error_msg)
            # Don't raise - return partial results
        
        return overall_results
    
    def upload_item_definition(
        self,
        workspace_id: str,
        item_name: str,
        item_type: str,
        definition_dir: Path,
        timeout: int = 300,
        semantic_model_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Upload/create item from PBIP definition
        
        Args:
            workspace_id: Target workspace GUID
            item_name: Display name for the item
            item_type: Type of item (Report, SemanticModel, etc.)
            definition_dir: Path to PBIP folder
            timeout: Timeout in seconds for polling (default 300s = 5 minutes)
            semantic_model_id: Optional semantic model ID for report connections
            
        Returns:
            Tuple of (success: bool, message: str, item_id: Optional[str])
        """
        import time
        
        logger.info(f"Uploading {item_type}: {item_name}")
        
        try:
            # Collect all files in definition directory
            parts = []
            
            for file_path in definition_dir.rglob("*"):
                if file_path.is_file():
                    # Get relative path
                    rel_path = file_path.relative_to(definition_dir)
                    
                    # Read file content
                    content = file_path.read_bytes()
                    
                    # If this is a report and we have a semantic model ID, update the connection
                    if item_type == "Report" and semantic_model_id and file_path.name == "definition.pbir":
                        try:
                            # Parse the definition file
                            definition_text = content.decode('utf-8')
                            definition_json = json.loads(definition_text)
                            
                            # Update the datasetReference with the new semantic model ID in connection string
                            if "datasetReference" in definition_json:
                                # Build the proper connection string with the new semantic model ID
                                connection_string = f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_id};Initial Catalog={item_name.replace('.Report', '')};Integrated Security=ClaimsToken;semanticmodelid={semantic_model_id}"
                                
                                definition_json["datasetReference"] = {
                                    "byConnection": {
                                        "connectionString": connection_string
                                    }
                                }
                                logger.info(f"Updated report connection to semantic model: {semantic_model_id}")
                                
                                # Re-encode the updated definition
                                content = json.dumps(definition_json, indent=2).encode('utf-8')
                        except Exception as e:
                            logger.warning(f"Could not update report connection: {e}")
                    
                    # Encode file
                    encoded = base64.b64encode(content).decode('utf-8')
                    
                    parts.append({
                        "path": str(rel_path).replace("\\", "/"),
                        "payload": encoded,
                        "payloadType": "InlineBase64"
                    })
            
            if not parts:
                return False, f"No files found in {definition_dir}", None
            
            logger.info(f"Collected {len(parts)} files for upload")
            
            # Create item payload
            payload = {
                "displayName": item_name,
                "type": item_type,
                "definition": {
                    "parts": parts
                }
            }
            
            # POST to create/update item
            response = self._make_request(
                "POST",
                f"/workspaces/{workspace_id}/items",
                json=payload
            )
            
            # Check if this is a long-running operation (LRO)
            if response.status_code == 202:
                # Get operation location from headers
                operation_url = response.headers.get("Location") or response.headers.get("Azure-AsyncOperation")
                
                if not operation_url:
                    logger.warning("Got 202 but no Location header for polling - assuming success")
                    return True, f"Upload initiated for {item_name}", None
                
                logger.info(f"Long-running upload operation started for {item_name}")
                logger.debug(f"Operation URL: {operation_url}")
                
                # Poll for completion
                start_time = time.time()
                retry_after = int(response.headers.get("Retry-After", 5))
                
                while time.time() - start_time < timeout:
                    time.sleep(retry_after)
                    
                    # Poll the operation status
                    poll_response = self._session.get(
                        operation_url,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    
                    if poll_response.status_code == 200:
                        try:
                            status_response = poll_response.json()
                            operation_status = status_response.get("status", "")
                            percent = status_response.get("percentComplete", 0)
                            
                            logger.debug(f"Upload status: {operation_status}, percent: {percent}%")
                            
                            if operation_status == "Succeeded":
                                # Try to get the item ID from status response or fetch from workspace
                                item_id = status_response.get("resourceId")
                                if not item_id:
                                    # Fetch the item from workspace by name
                                    try:
                                        items = self.get_workspace_items(workspace_id)
                                        for ws_item in items:
                                            if ws_item.get('displayName') == item_name and ws_item.get('type') == item_type:
                                                item_id = ws_item.get('id')
                                                break
                                    except:
                                        pass
                                logger.info(f"✓ Upload completed successfully for {item_name} - ID: {item_id}")
                                return True, f"Successfully uploaded {item_name}", item_id
                            
                            elif operation_status == "Failed":
                                error_info = status_response.get("error", {})
                                error_msg = error_info.get("message", "Unknown error")
                                error_code = error_info.get("code", "Unknown")
                                logger.error(f"Upload failed: {error_code} - {error_msg}")
                                return False, f"Upload failed: {error_msg}", None
                            
                            elif operation_status in ["NotStarted", "Running", "Undefined"]:
                                # Still in progress, continue polling
                                continue
                            else:
                                logger.warning(f"Unknown operation status: {operation_status}")
                                continue
                                
                        except Exception as e:
                            logger.error(f"Failed to parse status response: {e}")
                            continue
                    
                    elif poll_response.status_code == 404:
                        # Operation might have completed and been cleaned up
                        logger.warning("Operation URL returned 404 - assuming completion")
                        # Try to fetch item ID from workspace
                        item_id = None
                        try:
                            items = self.get_workspace_items(workspace_id)
                            for ws_item in items:
                                if ws_item.get('displayName') == item_name and ws_item.get('type') == item_type:
                                    item_id = ws_item.get('id')
                                    break
                        except:
                            pass
                        return True, f"Upload completed for {item_name} (operation completed)", item_id
                    else:
                        logger.warning(f"Poll returned status {poll_response.status_code}")
                        continue
                
                # Timeout reached
                logger.warning(f"Upload operation timed out after {timeout}s for {item_name}")
                return False, f"Upload timed out after {timeout}s - check Fabric workspace manually", None
            
            elif response.status_code in [200, 201]:
                # Immediate success - extract item ID from response
                try:
                    response_data = response.json()
                    item_id = response_data.get('id')
                    logger.info(f"✓ Uploaded {item_name} (immediate success) - ID: {item_id}")
                    return True, f"Successfully uploaded {item_name}", item_id
                except:
                    logger.info(f"✓ Uploaded {item_name} (immediate success)")
                    return True, f"Successfully uploaded {item_name}", None
            else:
                logger.error(f"Unexpected response status: {response.status_code}")
                return False, f"Unexpected response: {response.status_code}", None
            
        except Exception as e:
            error_msg = f"Failed to upload {item_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None


def load_config_from_file(config_path: Path) -> FabricConfig:
    """
    Load Fabric configuration from config.md file
    
    Args:
        config_path: Path to config.md
        
    Returns:
        FabricConfig object
        
    Raises:
        ValueError if config is invalid
    """
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")
    
    content = config_path.read_text(encoding='utf-8')
    
    # Parse config.md format:
    # tenantId = "..."
    # clientId = "..."
    # clientSecret = "..."
    
    config_data = {}
    for line in content.splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            if key in ['tenantId', 'clientId', 'clientSecret']:
                config_data[key] = value
    
    # Validate required fields
    required = ['tenantId', 'clientId', 'clientSecret']
    missing = [f for f in required if f not in config_data or not config_data[f]]
    
    if missing:
        raise ValueError(f"Missing required config fields: {', '.join(missing)}")
    
    return FabricConfig(
        tenant_id=config_data['tenantId'],
        client_id=config_data['clientId'],
        client_secret=config_data['clientSecret']
    )
