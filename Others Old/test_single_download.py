"""
Debug script to test single item download and see API response
"""

import sys
import logging
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.fabric_client import FabricClient, load_config_from_file

def test_single_item():
    """Test downloading a single report to see what the API returns"""
    print("=" * 60)
    print("DEBUG: Testing Single Item Download")
    print("=" * 60)
    print()
    
    try:
        # Load config
        config_path = Path("config.md")
        config = load_config_from_file(config_path)
        print(f"[OK] Config loaded")
        
        # Create client
        client = FabricClient(config)
        client.authenticate()
        print(f"[OK] Authenticated")
        print()
        
        # Get first workspace
        workspaces = client.list_workspaces()
        if not workspaces:
            print("[ERROR] No workspaces found")
            return
        
        workspace = workspaces[0]
        workspace_id = workspace["id"]
        workspace_name = workspace["displayName"]
        
        print(f"Testing with workspace: {workspace_name}")
        print(f"Workspace ID: {workspace_id}")
        print()
        
        # Get items
        items = client.get_workspace_items(workspace_id)
        print(f"Found {len(items)} items")
        print()
        
        # Find a Report
        report = None
        semantic_model = None
        
        for item in items:
            if item["type"] == "Report" and not report:
                report = item
            if item["type"] == "SemanticModel" and not semantic_model:
                semantic_model = item
        
        # Test Report
        if report:
            print("=" * 60)
            print(f"Testing Report: {report['displayName']}")
            print(f"Report ID: {report['id']}")
            print("=" * 60)
            print()
            
            definition = client.get_item_definition(workspace_id, report['id'])
            
            print(f"\nDefinition type: {type(definition)}")
            print(f"Definition keys: {list(definition.keys()) if definition else 'None'}")
            
            if definition and "definition" in definition:
                parts = definition["definition"].get("parts", [])
                print(f"Parts count: {len(parts)}")
                if parts:
                    print(f"First part keys: {list(parts[0].keys())}")
            print()
        
        # Test SemanticModel
        if semantic_model:
            print("=" * 60)
            print(f"Testing SemanticModel: {semantic_model['displayName']}")
            print(f"Model ID: {semantic_model['id']}")
            print("=" * 60)
            print()
            
            definition = client.get_item_definition(workspace_id, semantic_model['id'])
            
            print(f"\nDefinition type: {type(definition)}")
            print(f"Definition keys: {list(definition.keys()) if definition else 'None'}")
            
            if definition and "definition" in definition:
                parts = definition["definition"].get("parts", [])
                print(f"Parts count: {len(parts)}")
                if parts:
                    print(f"First part keys: {list(parts[0].keys())}")
            print()
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_item()
