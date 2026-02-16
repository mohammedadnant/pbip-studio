# Fabric CLI Integration - Quick Start Checklist

## ✅ Installation Checklist

- [ ] **Install ms-fabric-cli package**
  ```bash
  pip install ms-fabric-cli
  ```

- [ ] **Install all dependencies**
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **Verify installation**
  ```bash
  python -c "from fabric_cli import FabricClient; print('✓ Fabric CLI installed')"
  ```

## ✅ Quick Test Checklist

- [ ] **Run quick start script**
  ```bash
  python quick_start_fabric_cli.py
  ```

- [ ] **Authenticate successfully**
  - Opens browser for login
  - Returns to console after auth

- [ ] **List workspaces**
  - Displays at least one workspace
  - Shows workspace names and IDs

## ✅ Interface Testing Checklist

### Python Library
- [ ] **Import wrapper**
  ```python
  from src.services.fabric_cli_wrapper import FabricCLIWrapper
  ```

- [ ] **Create client and login**
  ```python
  client = FabricCLIWrapper()
  client.login()
  ```

- [ ] **List workspaces**
  ```python
  workspaces = client.list_workspaces()
  print(f"Found {len(workspaces)} workspaces")
  ```

- [ ] **List items in workspace**
  ```python
  items = client.list_workspace_items("workspace-id")
  print(f"Found {len(items)} items")
  ```

### Streamlit Web App
- [ ] **Start Streamlit server**
  ```bash
  streamlit run streamlit_app.py
  ```

- [ ] **Access in browser**
  - Opens http://localhost:8501
  - Shows welcome screen

- [ ] **Test authentication**
  - Select auth method
  - Click Login button
  - Verify "✓ Authenticated" status

- [ ] **Browse workspaces**
  - Click "Refresh Workspaces"
  - See workspace list
  - Select a workspace

- [ ] **View items**
  - Click "List Items"
  - See items table
  - Filter by type

- [ ] **Download an item**
  - Select an item
  - Choose format (TMDL/PBIP)
  - Click Download
  - Verify file saved

### Tkinter Desktop App
- [ ] **Launch app**
  ```bash
  python tkinter_app.py
  ```

- [ ] **Window opens**
  - Shows main window
  - All sections visible

- [ ] **Test authentication**
  - Select auth method
  - Click Login
  - See "✓ Authenticated" label

- [ ] **Load workspaces**
  - Click "Refresh Workspaces"
  - Dropdown populates

- [ ] **Load items**
  - Select workspace
  - Click "Load Items"
  - Tree view populates

- [ ] **Download item**
  - Select item in tree
  - Click "Download Selected"
  - Choose save location
  - Verify success message

### PyQt6 Integration (Optional)
- [ ] **Add import to main_window.py**
  ```python
  from gui.fabric_cli_tab import FabricCLITab
  ```

- [ ] **Add tab in init_ui()**
  ```python
  fabric_cli_tab = FabricCLITab()
  self.tabs.addTab(fabric_cli_tab, qta.icon('fa5s.cloud'), "Fabric CLI")
  ```

- [ ] **Run main application**
  ```bash
  python src/main.py
  ```

- [ ] **Verify tab appears**
  - "Fabric CLI" tab visible
  - Click to open

- [ ] **Test tab functionality**
  - Authentication works
  - Workspace loading works
  - Item browsing works
  - Download works

## ✅ Authentication Testing

### Interactive Browser Auth
- [ ] **Test with no credentials**
  ```python
  client = FabricCLIWrapper()
  client.login(interactive=True)
  ```
  - Browser opens
  - Login successful
  - Returns to app

### Service Principal Auth
- [ ] **Set up credentials**
  - Get tenant ID
  - Get client ID
  - Get client secret

- [ ] **Test with credentials**
  ```python
  client = FabricCLIWrapper(
      tenant_id="...",
      client_id="...",
      client_secret="..."
  )
  client.login(interactive=False)
  ```
  - No browser opens
  - Authentication succeeds

### Environment Variables Auth
- [ ] **Set environment variables**
  ```bash
  # PowerShell
  $env:AZURE_TENANT_ID = "your-tenant-id"
  $env:AZURE_CLIENT_ID = "your-client-id"
  $env:AZURE_CLIENT_SECRET = "your-secret"
  ```

- [ ] **Test with env vars**
  ```python
  client = FabricCLIWrapper(use_environment_vars=True)
  client.login(interactive=False)
  ```
  - Loads credentials from env
  - Authentication succeeds

## ✅ Download Testing

### Semantic Model (TMDL)
- [ ] **Download as TMDL**
  ```python
  client.download_semantic_model(
      workspace_id="ws-id",
      model_id="model-id",
      local_path="model.tmdl",
      format="TMDL"
  )
  ```
  - File/folder created
  - Contains model definition

### Semantic Model (PBIP)
- [ ] **Download as PBIP**
  ```python
  client.download_semantic_model(
      workspace_id="ws-id",
      model_id="model-id",
      local_path="model.pbip",
      format="PBIP"
  )
  ```
  - Folder created
  - Contains .pbip files

### Report (PBIP)
- [ ] **Download report**
  ```python
  client.download_report(
      workspace_id="ws-id",
      report_id="report-id",
      local_path="report.pbip"
  )
  ```
  - Folder created
  - Contains report definition

### Generic Download
- [ ] **Download any item**
  ```python
  client.download_item(
      workspace_id="ws-id",
      item_id="item-id",
      item_type="SemanticModel",
      local_path="item.tmdl",
      format="TMDL"
  )
  ```
  - Works for all item types
  - Proper error messages

## ✅ Error Handling Testing

### Package Not Installed
- [ ] **Uninstall temporarily**
  ```bash
  pip uninstall ms-fabric-cli -y
  ```

- [ ] **Try to use**
  ```python
  from src.services.fabric_cli_wrapper import FabricCLIWrapper
  client = FabricCLIWrapper()
  client.login()
  ```
  - Shows clear error message
  - Suggests `pip install ms-fabric-cli`

- [ ] **Reinstall**
  ```bash
  pip install ms-fabric-cli
  ```

### Invalid Credentials
- [ ] **Test with wrong credentials**
  ```python
  client = FabricCLIWrapper(
      tenant_id="wrong",
      client_id="wrong",
      client_secret="wrong"
  )
  client.login(interactive=False)
  ```
  - Raises exception
  - Clear error message

### Invalid Workspace ID
- [ ] **Test with fake ID**
  ```python
  items = client.list_workspace_items("fake-id-12345")
  ```
  - Raises exception
  - Error says workspace not found

### Invalid Item ID
- [ ] **Test with fake ID**
  ```python
  client.download_item("ws-id", "fake-item", "Report", "test.pbip")
  ```
  - Raises exception
  - Error says item not found

## ✅ Documentation Checklist

- [ ] **Read main documentation**
  - Open `FABRIC_CLI_INTEGRATION.md`
  - Review all sections
  - Understand authentication methods

- [ ] **Read implementation summary**
  - Open `FABRIC_CLI_IMPLEMENTATION_SUMMARY.md`
  - Review files created
  - Understand architecture

- [ ] **Read integration guide**
  - Open `INTEGRATION_GUIDE.md`
  - Know how to add to main app

- [ ] **Read feature comparison**
  - Open `FEATURE_COMPARISON.md`
  - Understand benefits over PowerShell

- [ ] **Check updated README**
  - Open `README.md`
  - See new Fabric CLI section

## ✅ Code Examples Tested

- [ ] **Example 1: List all workspaces**
  ```python
  from src.services.fabric_cli_wrapper import FabricCLIWrapper
  
  client = FabricCLIWrapper()
  client.login()
  
  for ws in client.list_workspaces():
      print(f"{ws['displayName']}: {ws['id']}")
  ```

- [ ] **Example 2: Batch download reports**
  ```python
  from src.services.fabric_cli_wrapper import FabricCLIWrapper
  from pathlib import Path
  
  client = FabricCLIWrapper()
  client.login()
  
  reports = client.list_workspace_items("ws-id", item_type="Report")
  for report in reports:
      path = Path("downloads") / f"{report.name}.pbip"
      client.download_report("ws-id", report.id, str(path))
      print(f"✓ {report.name}")
  ```

- [ ] **Example 3: Context manager**
  ```python
  from src.services.fabric_cli_wrapper import FabricCLIWrapper
  
  with FabricCLIWrapper() as client:
      client.login()
      workspaces = client.list_workspaces()
      print(f"Found {len(workspaces)} workspaces")
  ```

## ✅ Production Readiness

### Security
- [ ] **Credentials not in code**
  - Uses environment variables
  - Or secure credential store

- [ ] **Service principal permissions**
  - Minimum required permissions
  - Separate dev/prod principals

- [ ] **Secret rotation plan**
  - Documented process
  - Regular schedule

### Performance
- [ ] **Test with large workspace**
  - 100+ items
  - Downloads complete successfully

- [ ] **Test concurrent operations**
  - Multiple downloads
  - No conflicts

### Reliability
- [ ] **Test error recovery**
  - Network interruption
  - Invalid inputs
  - Clear error messages

- [ ] **Test logging**
  - All operations logged
  - Log level configurable

### Deployment
- [ ] **Test in clean environment**
  - Fresh Python install
  - Install from requirements.txt
  - Everything works

- [ ] **Test as packaged app**
  - Build with PyInstaller (optional)
  - Run on machine without Python
  - All features work

## ✅ Final Validation

### Smoke Test
```bash
# 5-minute smoke test
pip install -r requirements.txt
python quick_start_fabric_cli.py
streamlit run streamlit_app.py  # Test in browser
python tkinter_app.py  # Test desktop app
```

### Integration Test
```bash
# Run main application with new tab
python src/main.py
# Click Fabric CLI tab
# Login
# Download something
```

### User Acceptance
- [ ] **Show to stakeholder**
  - Demo all interfaces
  - Get feedback
  - Make adjustments

## 🎉 Completion Checklist

- [ ] All installation steps completed
- [ ] All interfaces tested
- [ ] All authentication methods work
- [ ] Downloads successful
- [ ] Error handling verified
- [ ] Documentation reviewed
- [ ] Code examples work
- [ ] Production ready
- [ ] Validated end-to-end

## 📝 Notes

Use this space to track issues or observations:

```
Issue: _______________________________________________
Solution: _____________________________________________

Issue: _______________________________________________
Solution: _____________________________________________

Issue: _______________________________________________
Solution: _____________________________________________
```

## ✅ Sign Off

- [ ] **Developer:** Tested all functionality _______________
- [ ] **QA:** Validated all scenarios _______________
- [ ] **User:** Approved for production _______________

---

**Status:** 
- [ ] Not Started
- [ ] In Progress
- [ ] Completed
- [ ] Production Ready

**Date:** _________________

**Signed:** _________________
