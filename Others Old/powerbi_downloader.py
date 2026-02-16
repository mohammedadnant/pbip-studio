"""
Power BI Service Downloader (Premium/Fabric Capacity)
Download Power BI datasets as TMDL format using XMLA endpoint

IMPORTANT: This is for Power BI Service workspaces, NOT Fabric workspaces.
For Fabric workspaces, use FabricClient instead (recommended).

LIMITATIONS:
- Requires Premium or Fabric capacity
- XMLA Read-Write must be enabled
- Downloads dataset ONLY (no report visuals)
- Service principal must have workspace access
"""

import subprocess
import os
import logging
from pathlib import Path
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class PowerBIDownloader:
    """
    Download Power BI datasets as TMDL format via XMLA endpoint
    
    This is a FALLBACK solution for classic Power BI Service workspaces
    that haven't been migrated to Microsoft Fabric yet.
    
    REQUIREMENTS:
    - Power BI Premium or Fabric capacity
    - XMLA endpoint enabled (Workspace Settings → Premium → XMLA Read-Write)
    - PowerShell 7+
    - SqlServer PowerShell module
    - Service principal with workspace Contributor/Admin role
    
    LIMITATIONS:
    - Dataset definition only (no report visuals)
    - No DAX queries or relationships in report
    - Requires Premium/Fabric capacity (not Pro)
    
    RECOMMENDED ALTERNATIVE:
    Use FabricClient for Fabric workspaces - it's simpler and more reliable.
    """
    
    def __init__(self):
        """Initialize PowerBI downloader with XMLA method"""
        self.base_dir = Path(__file__).parent.parent.parent
        logger.info("PowerBIDownloader initialized (XMLA method)")
    
    def download_dataset_as_tmdl(
        self,
        workspace_id: str,
        dataset_id: str,
        output_dir: str,
        config: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Download Power BI dataset as TMDL format via XMLA endpoint
        
        Args:
            workspace_id: Power BI workspace GUID
            dataset_id: Dataset GUID or name
            output_dir: Output directory path
            config: Auth config dict with keys:
                    - tenant_id
                    - client_id
                    - client_secret
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Downloading dataset {dataset_id} via XMLA endpoint")
        
        ps_script = self.base_dir / "scripts" / "download_tmdl.ps1"
        
        if not ps_script.exists():
            error_msg = f"PowerShell script not found: {ps_script}"
            logger.error(error_msg)
            return False, error_msg
        
        # Build PowerShell command
        cmd = [
            "pwsh.exe",
            "-ExecutionPolicy", "Bypass",
            "-File", str(ps_script),
            "-WorkspaceId", workspace_id,
            "-DatasetId", dataset_id,
            "-OutputPath", output_dir,
            "-TenantId", config.get("tenant_id", ""),
            "-ClientId", config.get("client_id", ""),
            "-ClientSecret", config.get("client_secret", "")
        ]
        
        try:
            logger.info("Executing PowerShell script for XMLA download...")
            logger.info("This may take several minutes for large datasets...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # Log output
            if result.stdout:
                logger.info(f"PowerShell output: {result.stdout}")
            
            if result.returncode == 0:
                success_msg = f"✓ Downloaded dataset to {output_dir}"
                logger.info(success_msg)
                return True, success_msg
            else:
                error_msg = f"PowerShell script failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
        
        except subprocess.TimeoutExpired:
            error_msg = "Download timed out after 10 minutes"
            logger.error(error_msg)
            return False, error_msg
        
        except FileNotFoundError:
            error_msg = "PowerShell (pwsh.exe) not found. Please install PowerShell 7+"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def test_connection(self, config: Dict[str, str]) -> Tuple[bool, str]:
        """
        Test if PowerShell and required modules are available
        
        Args:
            config: Auth config dict
        
        Returns:
            Tuple of (available: bool, message: str)
        """
        # Check PowerShell 7+ availability
        try:
            result = subprocess.run(
                ["pwsh.exe", "-Version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                ps_version = result.stdout.strip()
                return True, f"✓ PowerShell available: {ps_version}"
            else:
                return False, "PowerShell 7+ not found"
        
        except FileNotFoundError:
            return False, "PowerShell 7+ not installed. Download from: https://aka.ms/powershell"
        
        except Exception as e:
            return False, f"Error checking PowerShell: {str(e)}"


# Example usage
if __name__ == "__main__":
    import sys
    
    # Example configuration
    config = {
        "tenant_id": "your-tenant-id",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret"
    }
    
    # Create downloader
    downloader = PowerBIDownloader()
    
    # Test connection
    available, message = downloader.test_connection(config)
    print(f"Connection test: {message}")
    
    if available:
        print("\nIMPORTANT: Make sure you have:")
        print("  1. Premium or Fabric capacity")
        print("  2. XMLA Read-Write enabled in workspace settings")
        print("  3. Service principal has workspace Contributor role")
        print()
        
        # Download dataset
        success, result = downloader.download_dataset_as_tmdl(
            workspace_id="workspace-guid",
            dataset_id="dataset-guid-or-name",
            output_dir="./downloads",
            config=config
        )
        
        print(f"\nResult: {result}")
        sys.exit(0 if success else 1)
    else:
        print("Download method not available")
        sys.exit(1)
