# PowerShell Integration Fix for Installed App

## Current Issues Identified

1. **Fabric CLI not found**: When running from installed app, Python environment PATH is not inherited
2. **Script execution**: PowerShell scripts may not have proper execution context
3. **Authentication**: Service Principal auth might not work in subprocess context

## Solutions

### Solution 1: Replace PowerShell with Direct Python Implementation (RECOMMENDED)

Instead of calling PowerShell scripts that call Fabric CLI, use Python directly:

**Advantages:**
- No dependency on external Fabric CLI installation
- Works seamlessly in frozen executable
- Better error handling and progress reporting
- No PowerShell execution policy issues

**Implementation:**
- Use Microsoft Fabric REST API directly via `requests`
- Use Azure Identity library for authentication (MSAL)
- All logic in Python = fully portable

### Solution 2: Bundle Fabric CLI with Application

Package the Fabric CLI with your installer so it's always available.

### Solution 3: Fix PowerShell Execution (Quick Fix)

Improve the subprocess call to handle frozen app environment better.

## Recommended Approach: Python-Native Implementation

Replace `login.ps1` and `publish_to_fabric.ps1` with Python code using:

```python
import requests
from azure.identity import ClientSecretCredential

# Authenticate
credential = ClientSecretCredential(
    tenant_id=tenant_id,
    client_id=client_id,
    client_secret=client_secret
)

# Get token
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default")

# Call Fabric REST API
headers = {"Authorization": f"Bearer {token.token}"}
response = requests.get(
    "https://api.fabric.microsoft.com/v1/workspaces",
    headers=headers
)
```

This eliminates ALL PowerShell dependencies!
