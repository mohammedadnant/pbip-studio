# Microsoft Fabric CLI Integration Guide

## Overview

This project now includes **native Python integration** with Microsoft Fabric CLI, eliminating the need for PowerShell dependencies. The `ms-fabric-cli` Python package provides direct programmatic access to Fabric and Power BI workspaces.

## Key Benefits

✅ **No PowerShell Required** - Pure Python implementation  
✅ **Cross-Platform** - Works on Windows, Linux, and Mac  
✅ **Multiple Interfaces** - Web app, desktop app, and library  
✅ **Native API Access** - Direct calls to Fabric REST APIs  
✅ **PBIP/TMDL Support** - Download semantic models and reports in modern formats

---

## Installation

### Install Fabric CLI Package

```bash
pip install ms-fabric-cli
```

### Update All Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage Options

### 1. Python Library (Programmatic)

Use the `FabricCLIWrapper` class in your own code:

```python
from src.services.fabric_cli_wrapper import FabricCLIWrapper

# Initialize and authenticate
client = FabricCLIWrapper()
client.login()  # Opens browser for authentication

# List workspaces
workspaces = client.list_workspaces()
for ws in workspaces:
    print(f"{ws['displayName']}: {ws['id']}")

# List items in a workspace
items = client.list_workspace_items(workspace_id="<workspace-id>")

# Download semantic model as TMDL
client.download_semantic_model(
    workspace_id="<workspace-id>",
    model_id="<model-id>",
    local_path="./downloads/model.tmdl",
    format="TMDL"
)

# Download report as PBIP
client.download_report(
    workspace_id="<workspace-id>",
    report_id="<report-id>",
    local_path="./downloads/report.pbip"
)
```

### 2. Streamlit Web App

Run a web-based interface for browsing and downloading:

```bash
streamlit run streamlit_app.py
```

Features:
- 🌐 Web browser interface
- 🔐 Interactive or service principal authentication
- 📁 Browse all workspaces and items
- 📥 Download to browser
- 🚀 No installation required for end users

**Access:** http://localhost:8501

### 3. Tkinter Desktop App

Run a standalone desktop application:

```bash
python tkinter_app.py
```

Features:
- 🖥️ Native desktop UI
- 📦 Can be packaged as .exe
- 💾 Save directly to disk
- 🎨 Clean, professional interface

**Package as executable:**
```bash
pyinstaller --onefile --windowed tkinter_app.py
```

### 4. Integrated PyQt6 Tab

The main application now includes a Fabric CLI tab. To add it to your GUI:

```python
from gui.fabric_cli_tab import FabricCLITab

# In MainWindow.__init__:
fabric_tab = FabricCLITab()
self.tabs.addTab(fabric_tab, qta.icon('fa5s.cloud'), "Fabric CLI")
```

---

## Authentication Methods

### Interactive Browser (Recommended for Development)

```python
client = FabricCLIWrapper()
client.login(interactive=True)  # Opens browser
```

**Pros:**
- Easy to use
- No setup required
- Uses your Azure AD account

**Cons:**
- Requires user interaction
- Not suitable for automation

### Service Principal (Recommended for Production)

```python
client = FabricCLIWrapper(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-secret"
)
client.login(interactive=False)
```

**Setup:**
1. Register an app in Azure AD
2. Grant API permissions for Power BI Service
3. Create a client secret
4. Add service principal to workspace(s)

**Pros:**
- Non-interactive
- Ideal for automation
- Secure credential management

**Cons:**
- Requires Azure AD admin setup

### Environment Variables

Set credentials in environment variables:

```bash
# Windows PowerShell
$env:AZURE_TENANT_ID = "your-tenant-id"
$env:AZURE_CLIENT_ID = "your-client-id"
$env:AZURE_CLIENT_SECRET = "your-secret"

# Linux/Mac
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-secret"
```

Then authenticate:
```python
client = FabricCLIWrapper(use_environment_vars=True)
client.login(interactive=False)
```

---

## API Reference

### FabricCLIWrapper Class

#### Methods

**`__init__(tenant_id=None, client_id=None, client_secret=None, use_environment_vars=True)`**
- Initialize the Fabric CLI wrapper
- Can load credentials from parameters or environment variables

**`login(interactive=None) -> bool`**
- Authenticate to Microsoft Fabric
- `interactive=True`: Browser authentication
- `interactive=False`: Service principal authentication
- `interactive=None`: Auto-detect based on credentials

**`list_workspaces() -> List[Dict]`**
- List all accessible Fabric workspaces
- Returns list of workspace dictionaries

**`list_workspace_items(workspace_id, item_type=None) -> List[FabricItem]`**
- List items in a workspace
- Filter by `item_type` (e.g., 'SemanticModel', 'Report')

**`download_item(workspace_id, item_id, item_type, local_path, format='PBIP') -> Path`**
- Download any Fabric item
- Supported types: SemanticModel, Report, Dashboard, Dataflow, Lakehouse
- Supported formats: PBIP, TMDL

**`download_semantic_model(workspace_id, model_id, local_path, format='TMDL') -> Path`**
- Convenience method for downloading semantic models
- Default format is TMDL

**`download_report(workspace_id, report_id, local_path) -> Path`**
- Convenience method for downloading reports
- Always uses PBIP format

**`upload_item(workspace_id, local_path, item_type, item_name=None) -> Dict`**
- Upload a local item to Fabric workspace

**`get_item_definition(workspace_id, item_id) -> Dict`**
- Get detailed definition of a Fabric item

---

## Supported Item Types

| Type | Download Format | Description |
|------|----------------|-------------|
| **SemanticModel** | TMDL, PBIP | Power BI datasets/semantic models |
| **Report** | PBIP | Power BI reports |
| **Dashboard** | PBIP | Power BI dashboards |
| **Dataflow** | JSON | Power BI dataflows |
| **Lakehouse** | Metadata | Fabric lakehouses |

---

## File Formats

### PBIP (Power BI Project)
- Modern Power BI project format
- Git-friendly, text-based
- Contains report + semantic model
- Can be opened in Power BI Desktop

### TMDL (Tabular Model Definition Language)
- Human-readable semantic model format
- Git-friendly, text-based
- YAML-like structure
- Ideal for version control
- Requires Power BI Desktop with TMDL support

---

## Examples

### Example 1: Batch Download All Reports

```python
from src.services.fabric_cli_wrapper import FabricCLIWrapper
from pathlib import Path

client = FabricCLIWrapper()
client.login()

# Get all workspaces
workspaces = client.list_workspaces()

for ws in workspaces:
    ws_name = ws['displayName']
    ws_id = ws['id']
    
    # Get all reports in workspace
    reports = client.list_workspace_items(ws_id, item_type="Report")
    
    for report in reports:
        output_path = Path("downloads") / ws_name / f"{report.name}.pbip"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            client.download_report(ws_id, report.id, str(output_path))
            print(f"✓ Downloaded: {report.name}")
        except Exception as e:
            print(f"✗ Failed: {report.name} - {e}")
```

### Example 2: Download Semantic Model as TMDL

```python
from src.services.fabric_cli_wrapper import FabricCLIWrapper

client = FabricCLIWrapper()
client.login()

# Download semantic model in TMDL format
client.download_semantic_model(
    workspace_id="12345678-1234-1234-1234-123456789abc",
    model_id="87654321-4321-4321-4321-cba987654321",
    local_path="./models/sales_model.tmdl",
    format="TMDL"
)
```

### Example 3: Context Manager Usage

```python
from src.services.fabric_cli_wrapper import FabricCLIWrapper

with FabricCLIWrapper() as client:
    client.login()
    workspaces = client.list_workspaces()
    # ... do work ...
# Automatically cleaned up
```

### Example 4: Flask REST API

```python
from flask import Flask, jsonify, request
from src.services.fabric_cli_wrapper import FabricCLIWrapper

app = Flask(__name__)
client = FabricCLIWrapper()
client.login()

@app.route('/workspaces')
def get_workspaces():
    workspaces = client.list_workspaces()
    return jsonify(workspaces)

@app.route('/download', methods=['POST'])
def download_item():
    data = request.json
    result = client.download_item(
        workspace_id=data['workspace_id'],
        item_id=data['item_id'],
        item_type=data['item_type'],
        local_path=data['local_path']
    )
    return jsonify({'path': str(result)})

if __name__ == '__main__':
    app.run(debug=True)
```

---

## Comparison: PowerShell vs. Python

| Feature | PowerShell (Old) | Python (New) |
|---------|-----------------|--------------|
| **Platform** | Windows only | Cross-platform |
| **Dependencies** | PowerShell 7, Fabric CLI module | pip install ms-fabric-cli |
| **Integration** | subprocess calls | Native Python API |
| **Error Handling** | Parse stderr | Python exceptions |
| **Type Safety** | Limited | Full type hints |
| **IDE Support** | Limited | Full autocomplete |
| **Testing** | Difficult | Unit testable |
| **Deployment** | Complex | Simple |

---

## Troubleshooting

### Issue: "ms-fabric-cli not found"

**Solution:**
```bash
pip install ms-fabric-cli
```

### Issue: "Authentication failed"

**Solutions:**
1. Check Azure AD credentials are correct
2. Ensure service principal has workspace access
3. Verify tenant ID format (GUID)
4. Try interactive authentication first

### Issue: "Item not found"

**Solutions:**
1. Verify the workspace is a **Fabric workspace** (not classic Power BI)
2. Check item ID is correct
3. Ensure service principal has Read permissions
4. List workspace items first to verify ID

### Issue: "Download failed - format not supported"

**Solutions:**
1. Use TMDL for semantic models
2. Use PBIP for reports
3. Ensure Power BI Desktop supports the format
4. Check Fabric capacity is enabled

---

## Migration from PowerShell

If you're currently using PowerShell scripts:

### Before (PowerShell):
```python
import subprocess

result = subprocess.run([
    "powershell",
    "-File", "download_tmdl.ps1",
    "-WorkspaceId", workspace_id,
    "-ItemId", item_id
], capture_output=True)
```

### After (Python):
```python
from src.services.fabric_cli_wrapper import FabricCLIWrapper

client = FabricCLIWrapper()
client.login()
client.download_semantic_model(workspace_id, item_id, "./model.tmdl")
```

**Benefits:**
- ✅ 90% less code
- ✅ Better error handling
- ✅ No subprocess overhead
- ✅ Cross-platform compatible
- ✅ Type-safe and testable

---

## FAQ

**Q: Does this work with Power BI Service workspaces?**  
A: Yes! Fabric CLI works with both Fabric workspaces and Power BI Service workspaces (if they're in a Fabric/Premium capacity).

**Q: Can I download PBIX files?**  
A: No, Fabric CLI only supports PBIP/TMDL formats. For PBIX, use the Power BI REST API with `PowerBIDownloader`.

**Q: Do I need a Fabric capacity?**  
A: Yes, to download items from a workspace, it must be in a Fabric capacity or Premium capacity.

**Q: Can I use this in production?**  
A: Yes! Use service principal authentication for production deployments.

**Q: Is this officially supported by Microsoft?**  
A: Yes, `ms-fabric-cli` is an official Microsoft package for Fabric API access.

---

## Resources

- **Fabric CLI Documentation:** https://learn.microsoft.com/fabric/
- **Power BI REST API:** https://learn.microsoft.com/power-bi/developer/
- **Azure AD App Registration:** https://portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps
- **Fabric Workspace Setup:** https://learn.microsoft.com/fabric/get-started/

---

## Contributing

If you find issues or want to contribute improvements:

1. Test with both authentication methods
2. Ensure cross-platform compatibility
3. Add error handling for edge cases
4. Update documentation
5. Add unit tests if possible

---

## License

Same as parent project. See `LICENSE` file.

---

## Next Steps

1. **Try the Streamlit app:** `streamlit run streamlit_app.py`
2. **Integrate into your workflow:** Use `FabricCLIWrapper` in your scripts
3. **Package for distribution:** Build with PyInstaller for .exe distribution
4. **Add to CI/CD:** Automate downloads in your pipelines

**Happy Fabric CLI-ing! 🚀**
