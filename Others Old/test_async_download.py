"""
Test script for async Fabric API download with polling
"""
import requests
from azure.identity import ClientSecretCredential
import json
import time

# Load config
def load_config():
    with open('config.md', 'r') as f:
        content = f.read()
    
    import re
    tenant_id = re.search(r'tenantId\s*[=:]\s*["\']?([a-f0-9-]+)', content, re.I)
    client_id = re.search(r'clientId\s*[=:]\s*["\']?([a-f0-9-]+)', content, re.I)
    client_secret = re.search(r'clientSecret\s*[=:]\s*["\']?([^"\'\s]+)', content, re.I)
    
    return {
        'tenant_id': tenant_id.group(1) if tenant_id else None,
        'client_id': client_id.group(1) if client_id else None,
        'client_secret': client_secret.group(1) if client_secret else None
    }

# Get access token
print("Loading config...")
config = load_config()

print("\nAuthenticating...")
credential = ClientSecretCredential(
    tenant_id=config['tenant_id'],
    client_id=config['client_id'],
    client_secret=config['client_secret']
)

token = credential.get_token("https://analysis.windows.net/powerbi/api/.default")
print(f"✓ Got access token")

# Test download API with async polling
workspace_id = "756d0a12-1f02-4b86-8d90-68b65239c483"
item_id = "9f884ebd-0206-4354-b17c-6fe407e0acef"
format_type = "TMDL"

print(f"\nStep 1: Initiating download...")
print(f"Workspace: {workspace_id}")
print(f"Item: {item_id}")
print(f"Format: {format_type}")

url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{item_id}/getDefinition"
headers = {
    "Authorization": f"Bearer {token.token}",
    "Content-Type": "application/json"
}
body = {"format": format_type}

response = requests.post(url, headers=headers, json=body)

print(f"\nResponse Status: {response.status_code}")

if response.status_code == 202:
    operation_url = response.headers.get('Location')
    retry_after = int(response.headers.get('Retry-After', 5))
    
    print(f"✓ Async operation started")
    print(f"Operation URL: {operation_url}")
    print(f"Retry-After: {retry_after} seconds")
    
    # Poll for completion
    print(f"\nStep 2: Polling for completion...")
    max_attempts = 60
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\nAttempt {attempt}: Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        
        status_response = requests.get(operation_url, headers=headers)
        status_response.raise_for_status()
        
        status_data = status_response.json()
        status = status_data.get('status', 'Unknown')
        
        print(f"Status: {status}")
        print(f"Full status response: {json.dumps(status_data, indent=2)}")
        
        if status == 'Succeeded':
            print(f"\n{'='*80}")
            print("✓ Operation completed successfully!")
            print(f"Status response: {json.dumps(status_data, indent=2)}")
            
            # Get the actual result from /result endpoint
            print(f"\n{'='*80}")
            print("Step 3: Retrieving result from /result endpoint...")
            
            result_url = f"{operation_url}/result"
            print(f"GET {result_url}")
            
            result_response = requests.get(result_url, headers=headers)
            print(f"Result response status: {result_response.status_code}")
            
            if result_response.status_code == 200:
                print("✓ Got result!")
                result_data = result_response.json()
                print(f"\nResult keys: {list(result_data.keys()) if isinstance(result_data, dict) else type(result_data)}")
                
                if isinstance(result_data, dict):
                    print(f"\nFull result structure:")
                    print(json.dumps(result_data, indent=2)[:3000])
                    
                    if 'definition' in result_data:
                        definition = result_data['definition']
                        print(f"\n✓ Found 'definition' key")
                        print(f"Definition keys: {list(definition.keys())}")
                        
                        if 'parts' in definition:
                            parts = definition['parts']
                            print(f"\n✓ Found {len(parts)} parts:")
                            for i, part in enumerate(parts[:10]):
                                print(f"  Part {i+1}: {part.get('path')}, payloadType={part.get('payloadType')}, payload length={len(part.get('payload', ''))}")
            else:
                print(f"Failed to get result: {result_response.text[:500]}")
            
            break
        elif status in ['Failed', 'Cancelled']:
            error = status_data.get('error', {})
            print(f"✗ Operation {status}")
            print(f"Error: {json.dumps(error, indent=2)}")
            break
        elif status in ['Running', 'NotStarted']:
            print(f"  Still running...")
            continue
        else:
            print(f"  Unknown status: {status}")
            continue
    else:
        print("\n✗ Timeout after 60 attempts")
else:
    print(f"Unexpected status code: {response.status_code}")
    print(f"Response: {response.text}")

print(f"\n{'='*80}")
print("Test complete!")
