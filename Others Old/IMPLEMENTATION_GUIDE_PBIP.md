# Implementation Guide: Power BI PBIP/TMDL Download Solution

## 🎯 Problem Summary

**Power BI REST API cannot download reports in PBIP/TMDL format - only PBIX!**

Your Python `fabric_client.py` works great for **Microsoft Fabric**, but not for classic **Power BI Service**.

---

## 📋 Solution: Hybrid Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│          Python Application (main_window.py)     │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ↓                           ↓
┌───────────────┐          ┌────────────────────┐
│ FabricClient  │          │ PowerBIDownloader  │
│   (Python)    │          │  (Python wrapper)  │
└───────────────┘          └────────────────────┘
        │                           │
        ↓                           ↓
  Fabric REST API         PowerShell + XMLA Endpoint
  (PBIP/TMDL)            (TMDL via SqlServer module)
```

### When to Use Each

| Scenario | Use This | Format | Notes |
|----------|----------|--------|-------|
| Microsoft Fabric workspace | `FabricClient` | PBIP/TMDL | ✅ Already working |
| Power BI Service (Premium) | `PowerBIDownloader` | TMDL | ⚠️ Datasets only, requires XMLA |
| Power BI Service (Pro) | Not supported | N/A | ❌ Must use PBIX format |

---

## 🚀 Quick Start Implementation

### Step 1: Install PowerShell Script

The PowerShell script is already created at:
```
scripts/download_tmdl.ps1
```

**Test it manually:**
```powershell
cd "c:\Users\moham\Documents\Adnan Github Community\PowerBI-Desktop-App"

.\scripts\download_tmdl.ps1 `
    -WorkspaceId "your-workspace-guid" `
    -DatasetId "your-dataset-id-or-name" `
    -OutputPath ".\downloads" `
    -TenantId "your-tenant-id" `
    -ClientId "your-client-id" `
    -ClientSecret "your-client-secret"
```

### Step 2: Use PowerBIDownloader in Python

```python
from services.powerbi_downloader import PowerBIDownloader

# Configure
config = {
    "tenant_id": "your-tenant-id",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
}

# Create downloader
downloader = PowerBIDownloader(method="powershell-xmla")

# Test if available
available, message = downloader.test_connection(config)
print(f"Available: {available} - {message}")

# Download dataset as TMDL
success, result = downloader.download_dataset_as_tmdl(
    workspace_id="workspace-guid",
    dataset_id="dataset-name-or-id",
    output_dir="./downloads",
    config=config
)

if success:
    print(f"✓ {result}")
else:
    print(f"✗ {result}")
```

### Step 3: Update GUI (Optional)

Add download option in `src/gui/main_window.py`:

```python
from services.fabric_client import FabricClient, FabricConfig
from services.powerbi_downloader import PowerBIDownloader

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fabric_client = None
        self.powerbi_downloader = None
        
    def setup_downloaders(self):
        """Initialize both Fabric and Power BI downloaders"""
        
        config = {
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        # Fabric client for Fabric workspaces
        self.fabric_client = FabricClient(FabricConfig(**config))
        
        # Power BI downloader for Power BI Service
        self.powerbi_downloader = PowerBIDownloader(method="powershell-xmla")
        
    def download_workspace(self):
        """Download workspace - auto-detect source"""
        
        workspace_type = self.detect_workspace_type()
        
        if workspace_type == "fabric":
            # Use Fabric REST API
            return self.fabric_client.download_workspace(...)
        
        elif workspace_type == "powerbi":
            # Use PowerShell XMLA
            return self.powerbi_downloader.download_dataset_as_tmdl(...)
        
        else:
            return False, "Unknown workspace type"
```

---

## 📝 Requirements

### For Fabric Workspaces (Already Working)
- ✅ Python packages: `azure-identity`, `requests`
- ✅ Service Principal with Fabric workspace access

### For Power BI Service Workspaces (NEW)
- ⚠️ **Premium or Fabric capacity** (XMLA endpoint required)
- ⚠️ **PowerShell 7+** installed
- ⚠️ **SqlServer PowerShell module** (auto-installed by script)
- ⚠️ Service Principal with workspace access

**Check if you have Premium/Fabric:**
1. Go to workspace settings in Power BI Service
2. Look for "Premium" icon or "Fabric" capacity
3. Check if XMLA endpoint is enabled (Settings → Premium)

---

## 🧪 Testing

### Test 1: Fabric Workspace Download (Should Already Work)

```python
from services.fabric_client import FabricClient, FabricConfig

config = FabricConfig(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)

client = FabricClient(config)
client.authenticate()

# Download Fabric workspace
success, result = client.download_workspace(
    workspace_id="fabric-workspace-guid",
    workspace_name="MyFabricWorkspace",
    output_dir="./downloads"
)

print(result)
```

### Test 2: Power BI Dataset Download (NEW)

```python
from services.powerbi_downloader import PowerBIDownloader

config = {
    "tenant_id": "your-tenant-id",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
}

downloader = PowerBIDownloader(method="powershell-xmla")

# Test connection first
available, msg = downloader.test_connection(config)
print(f"PowerShell available: {available} - {msg}")

# Download dataset
if available:
    success, result = downloader.download_dataset_as_tmdl(
        workspace_id="powerbi-workspace-guid",
        dataset_id="dataset-name",
        output_dir="./downloads",
        config=config
    )
    print(result)
```

---

## ⚠️ Limitations & Workarounds

### Limitation 1: Power BI REST API - No PBIP/TMDL Support
**Workaround:** Use XMLA endpoint with PowerShell (provided solution)

### Limitation 2: XMLA Requires Premium/Fabric Capacity
**Workaround:** 
- Upgrade to Premium or Fabric capacity
- OR download as PBIX and manually convert in Power BI Desktop

### Limitation 3: XMLA Only Downloads Datasets (Not Reports)
**Workaround:** 
- Dataset TMDL is the most valuable part for migration
- Report layouts can be recreated or downloaded separately as PBIX

### Limitation 4: Power BI Pro Workspaces
**No TMDL solution available for Pro workspaces**
- Must use PBIX format
- Use REST API: `Export-PowerBIReport` to get PBIX
- Manually convert in Power BI Desktop

---

## 🔧 Troubleshooting

### Issue: "PowerShell not found"
**Solution:**
```powershell
# Install PowerShell 7+
winget install Microsoft.PowerShell
```

### Issue: "XMLA endpoint not enabled"
**Solution:**
1. Workspace must be on Premium/Fabric capacity
2. Enable in workspace settings
3. Contact admin if you don't have permissions

### Issue: "Authentication failed"
**Solution:**
1. Verify Service Principal has workspace access
2. Check credentials (tenant_id, client_id, client_secret)
3. Ensure API permissions are granted:
   - `Dataset.ReadWrite.All` for XMLA access

### Issue: "SqlServer module installation fails"
**Solution:**
```powershell
# Manual installation
Install-Module -Name SqlServer -Force -AllowClobber -Scope CurrentUser
```

### Issue: "Dataset not found"
**Solution:**
- Use dataset NAME, not display name
- Check dataset ID in Power BI Service URL
- List available datasets in PowerShell script output

---

## 📦 What's Included

### New Files Created:
1. ✅ `download_solution_options.md` - Detailed options comparison
2. ✅ `scripts/download_tmdl.ps1` - PowerShell XMLA downloader
3. ✅ `src/services/powerbi_downloader.py` - Python wrapper
4. ✅ `IMPLEMENTATION_GUIDE_PBIP.md` - This file

### Modified Files:
1. ✅ `src/services/fabric_client.py` - Added clarification comments

### Not Changed (Keep As-Is):
- `src/gui/main_window.py` - Works with Fabric already
- `requirements.txt` - Already has `azure-identity`
- `publish_to_fabric.ps1` - Still useful for uploads

---

## 🎓 Summary

### What Works Now:
✅ **Fabric workspaces** → Use `FabricClient` (Python REST API)

### What You Need to Add:
⚠️ **Power BI Service (Premium)** → Use `PowerBIDownloader` (PowerShell XMLA)

### What Won't Work:
❌ **Power BI Service (Pro)** → No TMDL support, use PBIX only

---

## 🚦 Next Steps

1. **Test PowerShell script manually**
   ```powershell
   .\scripts\download_tmdl.ps1 -WorkspaceId "..." -DatasetId "..." ...
   ```

2. **Test Python wrapper**
   ```python
   python -m src.services.powerbi_downloader
   ```

3. **Integrate into GUI** (optional)
   - Add workspace type detection
   - Show appropriate download option
   - Handle both Fabric and Power BI sources

4. **Document for users**
   - Update README with requirements
   - Explain Premium vs Pro limitations
   - Provide troubleshooting guide

---

## 📞 Support

If you encounter issues:

1. Check if workspace is Fabric or Power BI Service
2. Verify Premium/Fabric capacity if using XMLA
3. Test PowerShell script independently first
4. Check logs for detailed error messages

**Remember:** 
- Fabric workspaces → Use Python REST API ✅
- Power BI Premium → Use PowerShell XMLA ⚠️
- Power BI Pro → Use PBIX format only ❌
