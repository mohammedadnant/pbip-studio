# PowerShell to Python Migration - Complete Guide

## ✅ What Was Changed

### **OLD Approach (PowerShell-based)**
```
Python App → PowerShell.exe → login.ps1/publish_to_fabric.ps1 → fab CLI → Fabric API
```

**Problems:**
- ❌ Fabric CLI must be installed separately
- ❌ PowerShell execution policy issues
- ❌ PATH environment not available in frozen exe
- ❌ Subprocess complexity and error handling
- ❌ Fragile external dependencies

### **NEW Approach (Pure Python)**
```
Python App → FabricClient (Python) → Azure Identity → Fabric REST API
```

**Benefits:**
- ✅ No external CLI dependencies
- ✅ Works in frozen executable
- ✅ Better error handling
- ✅ Faster and more reliable
- ✅ Native Python - easier to maintain

---

## 📦 Files Modified

### 1. **New File: `src/services/fabric_client.py`**
   - Pure Python implementation of Fabric REST API client
   - Handles authentication using Azure Identity (MSAL)
   - Downloads workspaces as PBIP-TMDL format
   - Uploads items to Fabric workspaces

### 2. **Modified: `src/gui/main_window.py`**
   - **Import added:** `from services.fabric_client import FabricClient, FabricConfig, FabricAPIError`
   - **Method replaced:** `authenticate_and_list_workspaces()` - now uses Python REST API
   - **Method replaced:** `execute_publish()` - now uses Python REST API
   - **Removed:** All PowerShell subprocess calls

### 3. **Modified: `requirements.txt`**
   - **Added:** `azure-identity>=1.15.0`
   - **Added:** `msal>=1.26.0`

---

## 🔧 How It Works

### **Authentication Flow**
```python
# 1. Load config from config.md
config = FabricConfig.load_config_from_file(config_path)

# 2. Create client with service principal credentials
client = FabricClient(config)

# 3. Authenticate using Azure Identity (MSAL)
client.authenticate()
# → Gets OAuth token for Power BI API
# → Stores token in session headers
```

### **Download Workspaces**
```python
# 1. List all accessible workspaces
workspaces = client.list_workspaces()

# 2. For each workspace, get items
items = client.get_workspace_items(workspace_id)

# 3. For each item, get definition (PBIP format)
definition = client.get_item_definition(workspace_id, item_id, format="TMDL")

# 4. Extract and save files
for part in definition["definition"]["parts"]:
    path = part["path"]  # e.g., "report.json"
    payload = part["payload"]  # Base64 encoded content
    content = base64.b64decode(payload)
    file_path.write_bytes(content)
```

### **Upload Items**
```python
# 1. Find target workspace by name
workspaces = client.list_workspaces()
target_ws = [ws for ws in workspaces if ws["displayName"] == workspace_name][0]

# 2. Read all files from PBIP folder
parts = []
for file_path in definition_dir.rglob("*"):
    content = file_path.read_bytes()
    encoded = base64.b64encode(content).decode('utf-8')
    parts.append({"path": rel_path, "payload": encoded})

# 3. Upload to Fabric
client.upload_item_definition(workspace_id, item_name, item_type, definition_dir)
```

---

## 📝 API Endpoints Used

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| List workspaces | GET | `/v1/workspaces` |
| Get workspace items | GET | `/v1/workspaces/{id}/items` |
| Get item definition | POST | `/v1/workspaces/{id}/items/{id}/getDefinition` |
| Create/upload item | POST | `/v1/workspaces/{id}/items` |

**Base URL:** `https://api.fabric.microsoft.com`

**Authentication:** Bearer token (OAuth 2.0)
- Scope: `https://analysis.windows.net/powerbi/api/.default`

---

## 🧪 Testing

### **1. Test Authentication**
```powershell
cd "C:\Users\moham\Documents\Adnan Github Community\PowerBI-Desktop-App"
python test_fabric_client.py
```

**Expected output:**
```
============================================================
Testing Fabric REST API Client
============================================================
✓ Found config file: ...
✓ Configuration loaded
  Tenant ID: 12345678...
  Client ID: abcd1234...

🔐 Testing authentication...
✓ Authentication successful!

📁 Listing workspaces...
✓ Found 5 workspace(s)
  1. My Workspace (a1b2c3d4...)
  2. Sales Reports (e5f6g7h8...)
  ...

============================================================
✅ All tests passed!
============================================================
```

### **2. Test Download in Application**
1. Launch the application: `python src/main.py`
2. Go to **Configuration** tab
3. Ensure `config.md` has valid credentials
4. Go to **Download** tab
5. Click **"Authenticate & Download All Workspaces"**
6. Check `~/Documents/PowerBI-Toolkit-Downloads/FabricExport_YYYY-MM-DD_HHMMSS/`

### **3. Test Upload in Application**
1. Go to **Publish** tab
2. Browse to a PBIP folder
3. Select items to upload
4. Enter target workspace name
5. Click **"Publish to Fabric"**

---

## 🚀 Next Steps

### **Development Environment**
```powershell
# Install new dependencies
pip install azure-identity msal

# Test the application
python src/main.py
```

### **Building Installer**
```powershell
# Build MSI with new dependencies
python build_msi.ps1
```

The build script will automatically include `azure-identity` and `msal` packages in the frozen executable.

---

## 🔍 Troubleshooting

### **Authentication Errors**
```
Error: Authentication failed: AADSTS700016...
```
**Fix:** Check `config.md` credentials are correct
- Verify `tenantId`, `clientId`, `clientSecret`
- Ensure service principal has Fabric admin permissions

### **Module Not Found**
```
ModuleNotFoundError: No module named 'azure.identity'
```
**Fix:** Install dependencies
```powershell
pip install azure-identity msal
```

### **Workspace Not Found**
```
Error: Workspace 'MyWorkspace' not found
```
**Fix:** 
- Ensure workspace name is exact (case-sensitive)
- Verify service principal has access to workspace
- Create workspace in Fabric portal first

### **Upload Fails**
```
Error: API Error 400: Invalid definition format
```
**Fix:**
- Ensure you're uploading a valid PBIP folder structure
- Check that folder name ends with `.Report` or `.SemanticModel`
- Verify all required files exist (definition.pbir, report.json, etc.)

---

## 📊 Comparison

| Feature | PowerShell Approach | Python REST API |
|---------|-------------------|-----------------|
| **Dependencies** | Fabric CLI, PowerShell | azure-identity, msal |
| **Installation** | External (pip install) | Bundled in app |
| **Frozen Exe** | ❌ PATH issues | ✅ Works perfectly |
| **Error Handling** | ❌ Subprocess stderr | ✅ Python exceptions |
| **Speed** | ⚠️ Subprocess overhead | ✅ Direct API calls |
| **Reliability** | ⚠️ Environment-dependent | ✅ Consistent |
| **Maintenance** | ⚠️ Two languages | ✅ Pure Python |
| **Download Format** | PBIP-TMDL | PBIP-TMDL (same) |
| **Upload Format** | PBIP-TMDL | PBIP-TMDL (same) |

---

## ✨ Summary

**Before:**
- Required Fabric CLI installation
- PowerShell subprocess calls
- Fragile in frozen executable
- Complex error handling

**After:**
- Pure Python implementation
- Direct REST API calls
- Works in all environments
- Better error messages
- No external dependencies

**Result:** ✅ More reliable, faster, and easier to maintain!

---

## 🎯 Remaining PowerShell Files

The following PowerShell files are **NO LONGER USED** and can be removed:
- `login.ps1` (replaced by `FabricClient.authenticate()`)
- `publish_to_fabric.ps1` (replaced by `FabricClient.upload_item_definition()`)

However, they can be kept for reference or backward compatibility.

---

## 📞 Support

If you encounter any issues:
1. Run `test_fabric_client.py` to verify setup
2. Check application logs in `%LOCALAPPDATA%\PowerBI Migration Toolkit\logs\app.log`
3. Verify credentials in `%LOCALAPPDATA%\PowerBI Migration Toolkit\config.md`
4. Ensure service principal has Fabric permissions
