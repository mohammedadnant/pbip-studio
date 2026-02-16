"""
Test script for Power BI PBIP/TMDL download capabilities
Run this to verify your setup before integrating into the main application
"""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.fabric_client import FabricClient, FabricConfig, FabricAPIError
from services.powerbi_downloader import PowerBIDownloader


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def test_fabric_client():
    """Test if Fabric client is available"""
    print_header("Testing Fabric Client (for Fabric Workspaces)")
    
    try:
        # Check if azure-identity is installed
        from azure.identity import ClientSecretCredential
        print("✅ Azure Identity package installed")
        print("✅ FabricClient available for Fabric workspaces")
        print("\nUsage:")
        print("  - For Microsoft Fabric workspaces")
        print("  - Downloads PBIP/TMDL format")
        print("  - Pure Python, no external dependencies")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("\nInstall with: pip install azure-identity")
        return False


def test_powershell():
    """Test if PowerShell 7+ is available"""
    print_header("Testing PowerShell (for Power BI Service)")
    
    try:
        result = subprocess.run(
            ["pwsh.exe", "-Version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ PowerShell 7+ is installed")
            print(f"   Version: {result.stdout.strip()}")
            return True
        else:
            print("❌ PowerShell 7+ not found")
            return False
    
    except FileNotFoundError:
        print("❌ PowerShell 7+ not installed")
        print("\nInstall with: winget install Microsoft.PowerShell")
        return False
    
    except Exception as e:
        print(f"❌ Error checking PowerShell: {e}")
        return False


def test_powershell_script():
    """Test if PowerShell script exists"""
    print_header("Testing PowerShell Script")
    
    script_path = Path(__file__).parent / "scripts" / "download_tmdl.ps1"
    
    if script_path.exists():
        print(f"✅ Script found: {script_path}")
        print(f"   Size: {script_path.stat().st_size} bytes")
        return True
    else:
        print(f"❌ Script not found: {script_path}")
        return False


def test_powerbi_downloader():
    """Test PowerBIDownloader wrapper"""
    print_header("Testing PowerBIDownloader Wrapper")
    
    try:
        downloader = PowerBIDownloader(method="powershell-xmla")
        print("✅ PowerBIDownloader initialized")
        
        # Test connection without real credentials
        available, message = downloader.test_connection({})
        
        if available:
            print(f"✅ {message}")
        else:
            print(f"⚠️  {message}")
        
        print("\nUsage:")
        print("  - For Power BI Service (Premium/Fabric capacity)")
        print("  - Downloads TMDL format for datasets")
        print("  - Requires XMLA endpoint enabled")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def print_summary(results):
    """Print test summary"""
    print_header("Test Summary")
    
    fabric_ok = results["fabric"]
    powershell_ok = results["powershell"]
    script_ok = results["script"]
    downloader_ok = results["downloader"]
    
    print("Component Status:")
    print(f"  Fabric Client:        {'✅ Ready' if fabric_ok else '❌ Not Ready'}")
    print(f"  PowerShell 7+:        {'✅ Ready' if powershell_ok else '❌ Not Ready'}")
    print(f"  PowerShell Script:    {'✅ Ready' if script_ok else '❌ Not Ready'}")
    print(f"  PowerBI Downloader:   {'✅ Ready' if downloader_ok else '❌ Not Ready'}")
    
    print("\n" + "-" * 60)
    
    if fabric_ok:
        print("\n✅ You can download from FABRIC workspaces using FabricClient")
    else:
        print("\n❌ Fabric downloads not available - install azure-identity")
    
    if powershell_ok and script_ok and downloader_ok:
        print("✅ You can download from POWER BI SERVICE using PowerBIDownloader")
    else:
        print("❌ Power BI Service downloads not available")
        
        if not powershell_ok:
            print("   → Install PowerShell 7+")
        if not script_ok:
            print("   → Check if scripts/download_tmdl.ps1 exists")
        if not downloader_ok:
            print("   → Check Python wrapper implementation")
    
    print("\n" + "=" * 60)
    print("\nRecommendation:")
    
    if fabric_ok and (powershell_ok and script_ok and downloader_ok):
        print("  🎉 Everything is ready!")
        print("  • Use FabricClient for Fabric workspaces")
        print("  • Use PowerBIDownloader for Power BI Service")
    elif fabric_ok:
        print("  ⚠️  Partial setup:")
        print("  • FabricClient ready for Fabric workspaces")
        print("  • Install PowerShell 7+ for Power BI Service support")
    elif powershell_ok and script_ok:
        print("  ⚠️  Partial setup:")
        print("  • PowerBIDownloader ready for Power BI Service")
        print("  • Install azure-identity for Fabric support")
    else:
        print("  ❌ Setup incomplete")
        print("  • Install required components listed above")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Power BI PBIP/TMDL Download - Environment Check")
    print("=" * 60)
    
    results = {
        "fabric": test_fabric_client(),
        "powershell": test_powershell(),
        "script": test_powershell_script(),
        "downloader": test_powerbi_downloader()
    }
    
    print_summary(results)
    
    # Return exit code
    all_ok = all(results.values())
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
