"""
Test script to verify download capabilities
Tests both FabricClient and PowerBIDownloader
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.fabric_client import FabricClient, load_config_from_file
from services.powerbi_downloader import PowerBIDownloader

def test_fabric_client():
    """Test Fabric workspace download (PRIMARY METHOD)"""
    print("=" * 60)
    print("TEST 1: Fabric Client (Python REST API)")
    print("=" * 60)
    print()
    
    try:
        # Load config
        config_path = Path("config.md")
        if not config_path.exists():
            print("❌ config.md not found")
            print("   Create config.md with tenant_id, client_id, client_secret")
            return False
        
        config = load_config_from_file(config_path)
        print(f"✓ Config loaded from {config_path}")
        
        # Create client
        client = FabricClient(config)
        print("✓ FabricClient initialized")
        
        # Authenticate
        print("\nAuthenticating...")
        client.authenticate()
        print("✓ Authentication successful")
        
        # List workspaces
        print("\nListing workspaces...")
        workspaces = client.list_workspaces()
        print(f"✓ Found {len(workspaces)} workspace(s)")
        
        if workspaces:
            for ws in workspaces[:3]:  # Show first 3
                print(f"  - {ws.get('displayName')} (ID: {ws.get('id')})")
        
        print("\n✅ Fabric Client is WORKING")
        print("   This is the PRIMARY method for Fabric workspaces")
        print()
        return True
        
    except Exception as e:
        print(f"\n❌ Fabric Client test failed: {e}")
        print()
        return False


def test_powerbi_downloader():
    """Test PowerBI Service download (FALLBACK METHOD)"""
    print("=" * 60)
    print("TEST 2: PowerBI Downloader (PowerShell XMLA)")
    print("=" * 60)
    print()
    
    try:
        # Load config
        config_path = Path("config.md")
        if not config_path.exists():
            print("❌ config.md not found")
            return False
        
        config_dict = {}
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    if key == "tenantId":
                        config_dict["tenant_id"] = value
                    elif key == "clientId":
                        config_dict["client_id"] = value
                    elif key == "clientSecret":
                        config_dict["client_secret"] = value
        
        print(f"✓ Config loaded from {config_path}")
        
        # Create downloader
        downloader = PowerBIDownloader()
        print("✓ PowerBIDownloader initialized")
        
        # Test connection
        print("\nTesting PowerShell availability...")
        available, message = downloader.test_connection(config_dict)
        print(f"  {message}")
        
        if available:
            print("\n✅ PowerBI Downloader is AVAILABLE")
            print("   This is a FALLBACK method for Power BI Service")
            print("   Requirements:")
            print("   - Premium or Fabric capacity")
            print("   - XMLA Read-Write enabled")
            print("   - Downloads dataset only (no visuals)")
            print()
            return True
        else:
            print("\n⚠️ PowerBI Downloader not available")
            print("   Install PowerShell 7+: https://aka.ms/powershell")
            print()
            return False
        
    except Exception as e:
        print(f"\n❌ PowerBI Downloader test failed: {e}")
        print()
        return False


def main():
    """Run all tests"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Power BI Migration Toolkit - Tests" + " " * 14 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Test Fabric Client (PRIMARY)
    fabric_ok = test_fabric_client()
    
    # Test PowerBI Downloader (FALLBACK)
    powerbi_ok = test_powerbi_downloader()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"Fabric Client (Primary):        {'✅ WORKING' if fabric_ok else '❌ FAILED'}")
    print(f"PowerBI Downloader (Fallback):  {'✅ AVAILABLE' if powerbi_ok else '⚠️ NOT AVAILABLE'}")
    print()
    
    if fabric_ok:
        print("✅ Your application is ready to download from Fabric workspaces!")
        print()
        print("Next steps:")
        print("  1. Use FabricClient for all Fabric workspace downloads")
        print("  2. PowerBIDownloader is optional for Power BI Premium datasets")
        print()
    else:
        print("⚠️ Please check your configuration:")
        print("  1. Ensure config.md exists with valid credentials")
        print("  2. Verify service principal has Fabric workspace access")
        print("  3. Check network connectivity to api.fabric.microsoft.com")
        print()
    
    return fabric_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
