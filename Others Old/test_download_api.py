"""
Manual test script for Fabric API download endpoint
"""
import requests
from azure.identity import ClientSecretCredential
import json

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
print(f"Tenant ID: {config['tenant_id']}")
print(f"Client ID: {config['client_id']}")

print("\nAuthenticating...")
credential = ClientSecretCredential(
    tenant_id=config['tenant_id'],
    client_id=config['client_id'],
    client_secret=config['client_secret']
)

token = credential.get_token("https://analysis.windows.net/powerbi/api/.default")
print(f"✓ Got access token (expires: {token.expires_on})")

# Test download API
workspace_id = "756d0a12-1f02-4b86-8d90-68b65239c483"
item_id = "9f884ebd-0206-4354-b17c-6fe407e0acef"
format_type = "TMDL"

print(f"\nTesting download API...")
print(f"Workspace: {workspace_id}")
print(f"Item: {item_id}")
print(f"Format: {format_type}")

url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{item_id}/getDefinition"
headers = {
    "Authorization": f"Bearer {token.token}",
    "Content-Type": "application/json"
}
body = {"format": format_type}

print(f"\nPOST {url}")
print(f"Headers: {json.dumps({k: v[:50] + '...' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}")
print(f"Body: {json.dumps(body, indent=2)}")

response = requests.post(url, headers=headers, json=body)

print(f"\n{'='*80}")
print(f"Response Status: {response.status_code}")
print(f"Response Headers:")
for key, value in response.headers.items():
    print(f"  {key}: {value}")

print(f"\n{'='*80}")
print(f"Response Text Length: {len(response.text)}")
print(f"\nResponse Text Preview (first 1000 chars):")
print(response.text[:1000])

print(f"\n{'='*80}")
if response.text:
    try:
        data = response.json()
        print(f"JSON Parsed Successfully!")
        print(f"Type: {type(data)}")
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            print(f"\nJSON Structure:")
            print(json.dumps(data, indent=2)[:2000])
        else:
            print(f"Data: {data}")
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
else:
    print("Empty response!")

print(f"\n{'='*80}")
print("Test complete!")
