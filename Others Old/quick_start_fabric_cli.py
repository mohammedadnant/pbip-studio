"""
Quick Start Example for Fabric CLI Integration
Run this file to test the Fabric CLI wrapper
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.fabric_cli_wrapper import FabricCLIWrapper


def main():
    """Quick start example"""
    
    print("=" * 60)
    print("Microsoft Fabric CLI - Quick Start Example")
    print("=" * 60)
    print()
    
    # Initialize client (will auto-load from config.md)
    print("1. Initializing Fabric CLI client...")
    client = FabricCLIWrapper()
    
    # Authenticate using service principal from config.md
    print("2. Authenticating with service principal from config.md...")
    try:
        client.login(interactive=False)
        print("   ✓ Authentication successful!")
    except ImportError as e:
        print(f"   ✗ Error: {e}")
        print()
        print("   Please install Fabric CLI:")
        print("   pip install ms-fabric-cli")
        return
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
        return
    
    print()
    
    # List workspaces
    print("3. Fetching workspaces...")
    try:
        workspaces = client.list_workspaces()
        print(f"   ✓ Found {len(workspaces)} workspaces")
        print()
        
        # Display first 5 workspaces
        print("   First 5 workspaces:")
        for ws in workspaces[:5]:
            name = ws.get('displayName', ws.get('name', 'Unnamed'))
            print(f"   - {name}")
            print(f"     ID: {ws['id']}")
    except Exception as e:
        print(f"   ✗ Failed to list workspaces: {e}")
        return
    
    print()
    
    # Ask user if they want to explore a workspace
    print("4. Explore a workspace? (optional)")
    workspace_id = input("   Enter workspace ID (or press Enter to skip): ").strip()
    
    if workspace_id:
        print(f"   Loading items from workspace {workspace_id}...")
        try:
            items = client.list_workspace_items(workspace_id)
            print(f"   ✓ Found {len(items)} items")
            print()
            
            # Display items by type
            semantic_models = [i for i in items if i.type == "SemanticModel"]
            reports = [i for i in items if i.type == "Report"]
            
            if semantic_models:
                print(f"   Semantic Models ({len(semantic_models)}):")
                for item in semantic_models[:3]:
                    print(f"   - {item.name}")
            
            if reports:
                print(f"   Reports ({len(reports)}):")
                for item in reports[:3]:
                    print(f"   - {item.name}")
        except Exception as e:
            print(f"   ✗ Failed to list items: {e}")
    
    print()
    print("=" * 60)
    print("Quick start complete!")
    print()
    print("Next steps:")
    print("  - Run Streamlit web app: streamlit run streamlit_app.py")
    print("  - Run Tkinter desktop app: python tkinter_app.py")
    print("  - Read full docs: FABRIC_CLI_INTEGRATION.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
