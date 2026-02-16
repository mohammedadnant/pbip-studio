"""
Test Fabric REST API Client
Quick test to verify authentication and basic operations
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.fabric_client import FabricClient, FabricConfig, FabricAPIError, load_config_from_file


def test_authentication():
    """Test authentication with config.md"""
    print("=" * 60)
    print("Testing Fabric REST API Client")
    print("=" * 60)
    
    # Load config
    config_path = Path.home() / "AppData/Local/PowerBI Migration Toolkit/config.md"
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("\nPlease create config.md with:")
        print("tenantId = \"your-tenant-id\"")
        print("clientId = \"your-client-id\"")
        print("clientSecret = \"your-client-secret\"")
        return False
    
    print(f"✓ Found config file: {config_path}")
    
    try:
        config = load_config_from_file(config_path)
        print(f"✓ Configuration loaded")
        print(f"  Tenant ID: {config.tenant_id[:8]}...")
        print(f"  Client ID: {config.client_id[:8]}...")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    # Test authentication
    try:
        print("\n🔐 Testing authentication...")
        client = FabricClient(config)
        client.authenticate()
        print("✓ Authentication successful!")
    except FabricAPIError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test listing workspaces
    try:
        print("\n📁 Listing workspaces...")
        workspaces = client.list_workspaces()
        print(f"✓ Found {len(workspaces)} workspace(s)")
        
        for idx, ws in enumerate(workspaces[:5], 1):  # Show first 5
            ws_name = ws.get("displayName", ws.get("name", "Unknown"))
            ws_id = ws["id"]
            print(f"  {idx}. {ws_name} ({ws_id[:8]}...)")
        
        if len(workspaces) > 5:
            print(f"  ... and {len(workspaces) - 5} more")
            
    except Exception as e:
        print(f"❌ Failed to list workspaces: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nThe Fabric REST API client is working correctly.")
    print("You can now use the application to download and upload items.")
    
    return True


if __name__ == "__main__":
    success = test_authentication()
    sys.exit(0 if success else 1)
