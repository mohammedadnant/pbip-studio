# How to Integrate Fabric CLI Tab into Main Application

## Quick Integration

Add these lines to `src/gui/main_window.py`:

### 1. Add Import (at the top with other imports)

```python
from gui.fabric_cli_tab import FabricCLITab
```

### 2. Add Tab (in the `init_ui()` method, after existing tabs)

Find where the tabs are being created (look for lines like `self.tabs.addTab(...)`), then add:

```python
# Add Fabric CLI tab
fabric_cli_tab = FabricCLITab()
self.tabs.addTab(fabric_cli_tab, qta.icon('fa5s.cloud'), "Fabric CLI")
```

## Complete Example

If your `main_window.py` has this structure:

```python
def init_ui(self):
    """Initialize user interface"""
    # ... existing code ...
    
    # Tabs
    self.tabs = QTabWidget()
    
    # Existing tabs
    self.tabs.addTab(self.create_downloads_tab(), qta.icon('fa5s.download'), "Downloads")
    self.tabs.addTab(self.create_assessment_tab(), qta.icon('fa5s.chart-bar'), "Assessment")
    self.tabs.addTab(self.create_migration_tab(), qta.icon('fa5s.exchange-alt'), "Migration")
    
    # Add this:
    from gui.fabric_cli_tab import FabricCLITab
    fabric_cli_tab = FabricCLITab()
    self.tabs.addTab(fabric_cli_tab, qta.icon('fa5s.cloud'), "Fabric CLI")
    
    # ... rest of code ...
```

## Alternative: Lazy Loading

If you want to load the tab only when needed:

```python
def init_ui(self):
    # ... existing code ...
    
    # Tabs
    self.tabs = QTabWidget()
    self.tabs.addTab(self.create_downloads_tab(), qta.icon('fa5s.download'), "Downloads")
    self.tabs.addTab(self.create_assessment_tab(), qta.icon('fa5s.chart-bar'), "Assessment")
    self.tabs.addTab(self.create_migration_tab(), qta.icon('fa5s.exchange-alt'), "Migration")
    
    # Placeholder for Fabric CLI tab
    self.fabric_cli_tab = None
    placeholder = QWidget()
    placeholder_layout = QVBoxLayout(placeholder)
    placeholder_layout.addWidget(QLabel("Loading Fabric CLI..."))
    self.tabs.addTab(placeholder, qta.icon('fa5s.cloud'), "Fabric CLI")
    
    # Connect to tab change event
    self.tabs.currentChanged.connect(self.on_tab_changed)

def on_tab_changed(self, index):
    """Load Fabric CLI tab when first accessed"""
    if index == 3 and self.fabric_cli_tab is None:  # Adjust index based on your tabs
        from gui.fabric_cli_tab import FabricCLITab
        self.fabric_cli_tab = FabricCLITab()
        self.tabs.removeTab(3)
        self.tabs.insertTab(3, self.fabric_cli_tab, qta.icon('fa5s.cloud'), "Fabric CLI")
        self.tabs.setCurrentIndex(3)
```

## Icon Options

Choose from these Font Awesome icons:

```python
qta.icon('fa5s.cloud')           # Cloud icon (recommended)
qta.icon('fa5s.download')        # Download icon
qta.icon('fa5s.database')        # Database icon
qta.icon('fa5s.server')          # Server icon
qta.icon('fa5s.code')            # Code icon
qta.icon('mdi.microsoft-azure')  # Azure icon (if available)
```

## Testing

After integration:

1. Run the application: `python src/main.py`
2. Look for the "Fabric CLI" tab
3. Click on it
4. Try logging in with interactive authentication
5. Test workspace listing and downloads

## Troubleshooting

**Tab doesn't appear:**
- Check that the import statement is correct
- Verify `fabric_cli_tab.py` is in `src/gui/` folder
- Check for errors in console

**Tab appears but crashes:**
- Make sure `ms-fabric-cli` is installed: `pip install ms-fabric-cli`
- Check that all dependencies are installed
- Look for error messages in the log

**Authentication fails:**
- Verify internet connection
- Check Azure AD credentials if using service principal
- Try interactive authentication first

## Full File Locations

```
src/
├── gui/
│   ├── main_window.py          # Add import and tab here
│   └── fabric_cli_tab.py       # New file (already created)
└── services/
    └── fabric_cli_wrapper.py   # New file (already created)
```

## Next Steps After Integration

1. **Test the new tab:**
   - Open application
   - Navigate to Fabric CLI tab
   - Authenticate
   - Browse workspaces

2. **Customize styling:**
   - Match colors to your theme
   - Adjust layout if needed
   - Add custom icons

3. **Add shortcuts:**
   - Keyboard shortcuts for common actions
   - Quick access buttons
   - Integration with other tabs

4. **Enable persistence:**
   - Save last used workspace
   - Cache authentication
   - Remember user preferences

---

**That's it!** The Fabric CLI tab is now integrated into your application.
