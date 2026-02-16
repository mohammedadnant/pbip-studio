"""
Fabric Upload Tab - Upload Power BI items to Fabric workspace
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox,
    QGroupBox, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QHeaderView, QCheckBox, QSplitter, QRadioButton,
    QButtonGroup, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import qtawesome as qta
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from services.fabric_client import FabricClient, FabricConfig, load_config_from_file
from utils.backup_manager import get_latest_backup
from utils.pbir_connection_manager import restore_fabric_connection_string
from utils.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class FabricUploadAuthWorker(QThread):
    """Worker thread for authentication"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, object)  # success, client
    error = pyqtSignal(str)
    
    def __init__(self, config_path: str):
        super().__init__()
        self.config_path = config_path
    
    def run(self):
        try:
            self.progress.emit("Loading configuration...")
            config = load_config_from_file(Path(self.config_path))
            
            self.progress.emit("Authenticating to Fabric...")
            client = FabricClient(config)
            client.authenticate()
            
            self.finished.emit(True, client)
        except Exception as e:
            self.error.emit(f"Authentication failed: {str(e)}")


class FabricUploadWorkspaceWorker(QThread):
    """Worker thread for loading workspaces from Fabric"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, client: FabricClient):
        super().__init__()
        self.client = client
    
    def run(self):
        try:
            self.progress.emit("Loading workspaces from Fabric...")
            workspaces = self.client.list_workspaces()
            self.finished.emit(workspaces)
        except Exception as e:
            self.error.emit(f"Failed to load workspaces: {str(e)}")


class FabricUploadWorker(QThread):
    """Worker thread for uploading items to Fabric"""
    progress = pyqtSignal(str, int, int)  # message, current, total
    item_complete = pyqtSignal(str, bool, str)  # item_name, success, message
    finished = pyqtSignal(int, int)  # success_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, client: FabricClient, workspace_id: str, workspace_name: str,
                 items: List[Dict], base_path: Path):
        super().__init__()
        self.client = client
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name
        self.items = items
        self.base_path = base_path
    
    def run(self):
        try:
            total = len(self.items)
            success_count = 0
            
            # Sort items: Semantic Models first, then Reports
            semantic_models = [item for item in self.items if item['type'] == 'SemanticModel']
            reports = [item for item in self.items if item['type'] == 'Report']
            other_items = [item for item in self.items if item['type'] not in ['SemanticModel', 'Report']]
            
            sorted_items = semantic_models + reports + other_items
            
            # Map to store uploaded semantic model IDs
            semantic_model_ids = {}
            
            # Phase 1: Upload Semantic Models first
            for idx, item in enumerate(semantic_models, 1):
                item_name = item['name']
                item_type = item['type']
                item_path = item['path']
                
                self.progress.emit(f"Uploading {item_name} ({item_type})...", idx, total)
                
                try:
                    # Upload the semantic model
                    success, message, item_id = self.client.upload_item_definition(
                        workspace_id=self.workspace_id,
                        item_name=item_name,
                        item_type=item_type,
                        definition_dir=Path(item_path)
                    )
                    
                    if success:
                        success_count += 1
                        # Store the semantic model ID for report connections
                        if item_id:
                            semantic_model_ids[item_name] = item_id
                            self.item_complete.emit(item_name, True, f"✓ Uploaded successfully (ID: {item_id})")
                        else:
                            self.item_complete.emit(item_name, True, "✓ Uploaded successfully")
                    else:
                        self.item_complete.emit(item_name, False, f"✗ {message}")
                        
                except Exception as e:
                    error_msg = f"✗ Upload failed: {str(e)}"
                    self.item_complete.emit(item_name, False, error_msg)
            
            # Phase 2: Upload Reports with updated connections
            for idx, item in enumerate(reports, len(semantic_models) + 1):
                item_name = item['name']
                item_type = item['type']
                item_path = item['path']
                
                self.progress.emit(f"Uploading {item_name} ({item_type})...", idx, total)
                
                try:
                    # Step 1: Try to restore connection string from backup
                    # Find the semantic model path (parent directory of the report)
                    report_path = Path(item_path)
                    semantic_model_path = report_path.parent
                    
                    # Look for semantic model folder in same workspace
                    base_name = item_name.replace('.Report', '')
                    semantic_model_name = f"{base_name}.SemanticModel"
                    semantic_model_folder = semantic_model_path / semantic_model_name
                    
                    if semantic_model_folder.exists():
                        # Get latest backup for the semantic model
                        latest_backup = get_latest_backup(str(semantic_model_folder))
                        
                        if latest_backup:
                            backup_path = latest_backup['backup_path']
                            self.progress.emit(f"Restoring connection from backup for {item_name}...", idx, total)
                            
                            # Restore connection string from backup
                            restore_success, restore_msg = restore_fabric_connection_string(
                                str(report_path), 
                                backup_path
                            )
                            
                            if restore_success:
                                logger.info(f"Restored connection for {item_name}: {restore_msg}")
                            else:
                                logger.warning(f"Could not restore connection for {item_name}: {restore_msg}")
                    
                    # Step 2: Find matching semantic model ID
                    # Try to match by removing .Report suffix and adding .SemanticModel
                    semantic_model_id = semantic_model_ids.get(semantic_model_name)
                    
                    if semantic_model_id:
                        self.progress.emit(f"Updating {item_name} connection to semantic model {semantic_model_name}...", idx, total)
                    
                    # Step 3: Upload the report with semantic model ID
                    success, message, item_id = self.client.upload_item_definition(
                        workspace_id=self.workspace_id,
                        item_name=item_name,
                        item_type=item_type,
                        definition_dir=Path(item_path),
                        semantic_model_id=semantic_model_id
                    )
                    
                    if success:
                        success_count += 1
                        if semantic_model_id:
                            self.item_complete.emit(item_name, True, f"✓ Uploaded with connection to {semantic_model_name}")
                        else:
                            self.item_complete.emit(item_name, True, "✓ Uploaded successfully")
                    else:
                        self.item_complete.emit(item_name, False, f"✗ {message}")
                        
                except Exception as e:
                    error_msg = f"✗ Upload failed: {str(e)}"
                    self.item_complete.emit(item_name, False, error_msg)
            
            # Phase 3: Upload other items
            for idx, item in enumerate(other_items, len(semantic_models) + len(reports) + 1):
                item_name = item['name']
                item_type = item['type']
                item_path = item['path']
                
                self.progress.emit(f"Uploading {item_name} ({item_type})...", idx, total)
                
                try:
                    success, message, item_id = self.client.upload_item_definition(
                        workspace_id=self.workspace_id,
                        item_name=item_name,
                        item_type=item_type,
                        definition_dir=Path(item_path)
                    )
                    
                    if success:
                        success_count += 1
                        self.item_complete.emit(item_name, True, "✓ Uploaded successfully")
                    else:
                        self.item_complete.emit(item_name, False, f"✗ {message}")
                        
                except Exception as e:
                    error_msg = f"✗ Upload failed: {str(e)}"
                    self.item_complete.emit(item_name, False, error_msg)
            
            self.finished.emit(success_count, total)
            
        except Exception as e:
            self.error.emit(f"Upload process failed: {str(e)}")


class FabricUploadTab(QWidget):
    """Tab for uploading Power BI items to Fabric workspace"""
    
    def __init__(self, downloads_base: Path, parent=None):
        super().__init__(parent)
        self.downloads_base = downloads_base
        self.client: Optional[FabricClient] = None
        self.authenticated = False
        self.selected_folder: Optional[Path] = None
        self.local_workspaces: List[Dict] = []
        self.local_items: List[Dict] = []
        self.fabric_workspaces: List[Dict] = []
        self.theme_manager = get_theme_manager()
        
        self.init_ui()
        
        # Auto-authenticate on load
        self.auto_authenticate()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header with status
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("☁️ Microsoft Fabric CLI")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(title)
        
        self.status_label = QLabel("● Not Connected")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        header_layout.addWidget(self.status_label)
        
        # Add info message in header
        info_label = QLabel("  |  ℹ️ Semantic Models → Reports with updated connections")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(info_label)
        
        header_layout.addStretch()
        
        self.auth_btn = QPushButton(qta.icon('fa5s.sync'), " Reconnect")
        self.auth_btn.clicked.connect(self.auto_authenticate)
        self.auth_btn.setEnabled(False)
        header_layout.addWidget(self.auth_btn)
        
        layout.addWidget(header)
        
        # 1. Folder Selection Section (TOP)
        folder_group = QGroupBox("1️⃣ Select Local Power BI Folder")
        folder_layout = QVBoxLayout()
        
        folder_browse_layout = QHBoxLayout()
        folder_browse_layout.addWidget(QLabel("Folder path:"))
        self.folder_path_label = QLabel("No folder selected")
        self.folder_path_label.setStyleSheet("color: #666; padding: 5px; font-size: 11px;")
        folder_browse_layout.addWidget(self.folder_path_label, 1)
        
        self.browse_folder_btn = QPushButton(qta.icon('fa5s.folder-open'), " Browse")
        self.browse_folder_btn.clicked.connect(self.browse_local_folder)
        folder_browse_layout.addWidget(self.browse_folder_btn)
        
        folder_layout.addLayout(folder_browse_layout)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Create splitter for side-by-side workspace and items tables
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT: Local Workspaces Table
        workspace_widget = QWidget()
        workspace_main_layout = QVBoxLayout(workspace_widget)
        workspace_main_layout.setContentsMargins(0, 0, 0, 0)
        
        workspace_group = QGroupBox("2️⃣ Select Workspace from Local Folder")
        workspace_layout = QVBoxLayout()
        
        self.local_workspaces_table = QTableWidget()
        self.local_workspaces_table.setColumnCount(2)
        self.local_workspaces_table.setHorizontalHeaderLabels(["Select", "Workspace Name"])
        self.local_workspaces_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.local_workspaces_table.setColumnWidth(0, 60)
        self.local_workspaces_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.local_workspaces_table.setMinimumHeight(150)
        self.local_workspaces_table.setMaximumHeight(300)
        self.local_workspaces_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.local_workspaces_table.itemChanged.connect(self.on_workspace_item_changed)
        workspace_layout.addWidget(self.local_workspaces_table)
        
        workspace_group.setLayout(workspace_layout)
        workspace_main_layout.addWidget(workspace_group)
        splitter.addWidget(workspace_widget)
        
        # RIGHT: Local Items Table
        items_widget = QWidget()
        items_main_layout = QVBoxLayout(items_widget)
        items_main_layout.setContentsMargins(0, 0, 0, 0)
        
        items_group = QGroupBox("3️⃣ Select Items to Upload")
        items_layout = QVBoxLayout()
        items_layout.setSpacing(0)
        items_layout.setContentsMargins(5, 5, 5, 5)
        
        items_controls = QHBoxLayout()
        items_controls.addWidget(QLabel("Items in selected workspace:"))
        
        self.select_all_items_btn = QPushButton(qta.icon('fa5s.check-square'), "Select All")
        self.select_all_items_btn.clicked.connect(self.select_all_items)
        items_controls.addWidget(self.select_all_items_btn)
        
        self.deselect_all_items_btn = QPushButton(qta.icon('fa5s.square'), "Deselect All")
        self.deselect_all_items_btn.clicked.connect(self.deselect_all_items)
        items_controls.addWidget(self.deselect_all_items_btn)
        
        items_controls.addStretch()
        items_layout.addLayout(items_controls)
        
        self.local_items_table = QTableWidget()
        self.local_items_table.setColumnCount(3)
        self.local_items_table.setHorizontalHeaderLabels(["Select", "Name", "Type"])
        self.local_items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.local_items_table.setColumnWidth(0, 60)
        self.local_items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.local_items_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.local_items_table.setMinimumHeight(150)
        self.local_items_table.setMaximumHeight(300)
        self.local_items_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.local_items_table.itemChanged.connect(self.on_item_changed)
        items_layout.addWidget(self.local_items_table)
        
        items_group.setLayout(items_layout)
        items_main_layout.addWidget(items_group)
        splitter.addWidget(items_widget)
        
        # Set splitter sizes to give more space
        splitter.setSizes([350, 650])
        
        layout.addWidget(splitter)
        
        # 4. Destination Workspace Selection - Compact layout
        dest_group = QGroupBox("4️⃣ Select Destination Workspace")
        dest_layout = QVBoxLayout()
        
        # Single row with radio buttons, dropdown, refresh, and upload button
        action_layout = QHBoxLayout()
        
        # Radio buttons
        self.workspace_btn_group = QButtonGroup()
        
        self.same_workspace_radio = QRadioButton("Same Workspace")
        self.same_workspace_radio.setChecked(True)
        self.same_workspace_radio.toggled.connect(self.on_workspace_selection_changed)
        self.workspace_btn_group.addButton(self.same_workspace_radio)
        action_layout.addWidget(self.same_workspace_radio)
        
        self.other_workspace_radio = QRadioButton("Other Workspace:")
        self.other_workspace_radio.toggled.connect(self.on_workspace_selection_changed)
        self.workspace_btn_group.addButton(self.other_workspace_radio)
        action_layout.addWidget(self.other_workspace_radio)
        
        # Workspace selection combo - compact width
        self.fabric_workspace_combo = QComboBox()
        self.fabric_workspace_combo.setEnabled(False)
        self.fabric_workspace_combo.setMinimumWidth(275)
        self.fabric_workspace_combo.setMaximumWidth(375)
        action_layout.addWidget(self.fabric_workspace_combo)
        
        # Refresh button
        self.refresh_fabric_ws_btn = QPushButton(qta.icon('fa5s.sync'), "")
        self.refresh_fabric_ws_btn.setToolTip("Refresh workspaces from Fabric")
        self.refresh_fabric_ws_btn.clicked.connect(self.load_fabric_workspaces)
        self.refresh_fabric_ws_btn.setEnabled(False)
        self.refresh_fabric_ws_btn.setMaximumWidth(40)
        action_layout.addWidget(self.refresh_fabric_ws_btn)
        
        action_layout.addStretch()
        
        # Upload button - now in same row, pushed to right
        self.upload_btn = QPushButton(qta.icon('fa5s.cloud-upload-alt'), " Upload Selected Items")
        self.apply_upload_button_style()
        self.upload_btn.clicked.connect(self.start_upload)
        self.upload_btn.setEnabled(False)
        action_layout.addWidget(self.upload_btn)
        dest_layout.addLayout(action_layout)
        
        # Progress bar
        self.upload_progress_bar = QProgressBar()
        self.upload_progress_bar.setVisible(False)
        self.upload_progress_bar.setTextVisible(True)
        self.upload_progress_bar.setMinimumHeight(25)
        dest_layout.addWidget(self.upload_progress_bar)
        
        dest_group.setLayout(dest_layout)
        dest_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(dest_group)
        
        # Activity Log - fixed height to prevent expansion
        log_group = QGroupBox("📋 Activity Log")
        log_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(5, 5, 5, 5)
        
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMinimumHeight(120)
        self.activity_log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background: #34495e; color: #ecf0f1; padding: 8px;")
        self.activity_log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        log_layout.addWidget(self.activity_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        layout.addStretch(0)  # Add stretch at the end to prevent expansion
    
    def log_message(self, message: str):
        """Add message to activity log (newest first)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Insert at the beginning instead of appending
        cursor = self.activity_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertText(f"[{timestamp}] {message}\n")
        self.activity_log.setTextCursor(cursor)
    
    def auto_authenticate(self):
        """Auto-authenticate using config.md"""
        self.log_message("Starting auto-authentication...")
        self.status_label.setText("● Connecting...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.auth_btn.setEnabled(False)
        
        # Find config.md
        config_path = Path("config.md")
        if not config_path.exists():
            config_path = Path.cwd() / "config.md"
        if not config_path.exists():
            config_path = Path(__file__).parent.parent.parent / "config.md"
        
        if not config_path.exists():
            self.log_message("❌ config.md not found")
            self.status_label.setText("● Config Not Found")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.auth_btn.setEnabled(True)
            QMessageBox.warning(self, "Config Not Found", 
                "config.md file not found. Please ensure it exists in the project root.")
            return
        
        # Start authentication worker
        self.auth_worker = FabricUploadAuthWorker(str(config_path))
        self.auth_worker.progress.connect(self.log_message)
        self.auth_worker.finished.connect(self.on_auth_complete)
        self.auth_worker.error.connect(self.on_auth_error)
        self.auth_worker.start()
    
    def on_auth_complete(self, success: bool, client: FabricClient):
        """Handle authentication completion"""
        if success:
            self.client = client
            self.authenticated = True
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.log_message("✓ Authentication successful")
            self.auth_btn.setEnabled(True)
            self.refresh_fabric_ws_btn.setEnabled(True)
            
            # Auto-load fabric workspaces
            self.load_fabric_workspaces()
        else:
            self.on_auth_error("Authentication failed")
    
    def on_auth_error(self, error: str):
        """Handle authentication error"""
        self.authenticated = False
        self.status_label.setText("● Connection Failed")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.log_message(f"❌ {error}")
        self.auth_btn.setEnabled(True)
        QMessageBox.critical(self, "Authentication Error", error)
    
    def set_folder_path(self, folder_path: str):
        """Set the folder path programmatically (e.g., from Assessment tab)"""
        if folder_path and Path(folder_path).exists():
            self.selected_folder = Path(folder_path)
            self.folder_path_label.setText(str(self.selected_folder))
            self.folder_path_label.setStyleSheet("color: #0078D4; padding: 5px; font-size: 11px;")
            self.log_message(f"Selected folder: {self.selected_folder}")
            
            # Scan the folder for workspaces
            self.scan_local_folder()
    
    def browse_local_folder(self):
        """Browse for local Power BI folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Power BI Download Folder",
            str(self.downloads_base)
        )
        
        if folder:
            self.set_folder_path(folder)
    
    def scan_local_folder(self):
        """Scan the selected folder for workspaces and items"""
        if not self.selected_folder:
            return
        
        self.log_message("Scanning folder for workspaces...")
        self.local_workspaces = []
        
        # Look for workspaces_hierarchy.json or scan directory structure
        hierarchy_file = self.selected_folder / "workspaces_hierarchy.json"
        
        if hierarchy_file.exists():
            # Load from hierarchy file
            try:
                with open(hierarchy_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                workspaces = data.get('workspaces', [])
                for ws in workspaces:
                    self.local_workspaces.append({
                        'name': ws.get('name', 'Unknown'),
                        'id': ws.get('id', ''),
                        'path': self.selected_folder / ws.get('name', '')
                    })
                    
                self.log_message(f"Found {len(self.local_workspaces)} workspaces from hierarchy file")
            except Exception as e:
                self.log_message(f"Error reading hierarchy file: {str(e)}")
                self.scan_folder_structure()
        else:
            # Scan folder structure
            self.scan_folder_structure()
        
        # Populate workspaces table
        self.populate_workspaces_table()
    
    def scan_folder_structure(self):
        """Scan folder structure for workspace folders"""
        if not self.selected_folder:
            return
        
        # Look for Raw Files or Processed_Data folders
        raw_files = self.selected_folder / "Raw Files"
        processed_data = self.selected_folder / "Processed_Data"
        
        scan_dir = processed_data if processed_data.exists() else raw_files if raw_files.exists() else self.selected_folder
        
        if scan_dir.exists() and scan_dir.is_dir():
            for workspace_dir in scan_dir.iterdir():
                if workspace_dir.is_dir():
                    self.local_workspaces.append({
                        'name': workspace_dir.name,
                        'id': '',
                        'path': workspace_dir
                    })
        
        self.log_message(f"Found {len(self.local_workspaces)} workspaces from folder structure")
    
    def populate_workspaces_table(self):
        """Populate the local workspaces table"""
        self.local_workspaces_table.setRowCount(0)
        
        for ws in self.local_workspaces:
            row = self.local_workspaces_table.rowCount()
            self.local_workspaces_table.insertRow(row)
            
            # Checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            self.local_workspaces_table.setItem(row, 0, checkbox_item)
            
            # Workspace name
            name_item = QTableWidgetItem(ws['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.local_workspaces_table.setItem(row, 1, name_item)
        
        self.log_message(f"Loaded {len(self.local_workspaces)} workspaces into table")
    
    def on_workspace_item_changed(self, item: QTableWidgetItem):
        """Handle workspace checkbox change"""
        if item.column() == 0:  # Only handle checkbox column
            row = item.row()
            self.on_workspace_selected(row)
    
    def on_workspace_selected(self, row: int):
        """Handle workspace selection"""
        # Uncheck other workspaces (single selection)
        for r in range(self.local_workspaces_table.rowCount()):
            if r != row:
                checkbox_item = self.local_workspaces_table.item(r, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.CheckState.Unchecked)
        
        # Load items for selected workspace
        checkbox_item = self.local_workspaces_table.item(row, 0)
        if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
            workspace = self.local_workspaces[row]
            self.load_local_items(workspace)
        else:
            self.local_items_table.setRowCount(0)
            self.local_items = []
    
    def load_local_items(self, workspace: Dict):
        """Load items from selected workspace folder"""
        self.log_message(f"Loading items from workspace: {workspace['name']}")
        self.local_items = []
        
        workspace_path = workspace['path']
        if not workspace_path.exists():
            self.log_message(f"Workspace path not found: {workspace_path}")
            return
        
        # Scan for .pbip folders (both Reports and SemanticModels)
        for item_dir in workspace_path.iterdir():
            if item_dir.is_dir():
                # Check for definition files to determine item type
                definition_pbir = item_dir / "definition.pbir"
                definition_pbism = item_dir / "definition.pbism"
                
                item_type = None
                if definition_pbir.exists():
                    item_type = "Report"
                elif definition_pbism.exists():
                    item_type = "SemanticModel"
                
                if item_type:
                    self.local_items.append({
                        'name': item_dir.name,
                        'type': item_type,
                        'path': str(item_dir)
                    })
        
        self.log_message(f"Found {len(self.local_items)} items in workspace")
        self.populate_items_table()
    
    def populate_items_table(self):
        """Populate the local items table"""
        self.local_items_table.setRowCount(0)
        
        for item in self.local_items:
            row = self.local_items_table.rowCount()
            self.local_items_table.insertRow(row)
            
            # Checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            self.local_items_table.setItem(row, 0, checkbox_item)
            
            # Item name
            name_item = QTableWidgetItem(item['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.local_items_table.setItem(row, 1, name_item)
            
            # Item type
            type_item = QTableWidgetItem(item['type'])
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.local_items_table.setItem(row, 2, type_item)
        
        self.update_upload_button()
    
    def on_item_changed(self, item: QTableWidgetItem):
        """Handle item checkbox change"""
        if item.column() == 0:  # Only handle checkbox column
            self.update_upload_button()
    
    def select_all_items(self):
        """Select all items in the table"""
        for row in range(self.local_items_table.rowCount()):
            checkbox_item = self.local_items_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)
        self.update_upload_button()
    
    def deselect_all_items(self):
        """Deselect all items in the table"""
        for row in range(self.local_items_table.rowCount()):
            checkbox_item = self.local_items_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
        self.update_upload_button()
    
    def on_workspace_selection_changed(self):
        """Handle workspace selection mode change"""
        is_other = self.other_workspace_radio.isChecked()
        self.fabric_workspace_combo.setEnabled(is_other)
        self.update_upload_button()
    
    def load_fabric_workspaces(self):
        """Load available workspaces from Fabric"""
        if not self.authenticated or not self.client:
            self.log_message("Not authenticated to Fabric")
            return
        
        self.log_message("Loading workspaces from Fabric...")
        self.refresh_fabric_ws_btn.setEnabled(False)
        
        self.workspace_worker = FabricUploadWorkspaceWorker(self.client)
        self.workspace_worker.progress.connect(self.log_message)
        self.workspace_worker.finished.connect(self.on_fabric_workspaces_loaded)
        self.workspace_worker.error.connect(self.on_fabric_workspaces_error)
        self.workspace_worker.start()
    
    def on_fabric_workspaces_loaded(self, workspaces: List):
        """Handle Fabric workspaces loaded"""
        self.fabric_workspaces = workspaces
        self.fabric_workspace_combo.clear()
        
        for ws in workspaces:
            self.fabric_workspace_combo.addItem(ws['displayName'], ws['id'])
        
        self.log_message(f"Loaded {len(workspaces)} workspaces from Fabric")
        self.refresh_fabric_ws_btn.setEnabled(True)
    
    def on_fabric_workspaces_error(self, error: str):
        """Handle error loading Fabric workspaces"""
        self.log_message(f"❌ {error}")
        self.refresh_fabric_ws_btn.setEnabled(True)
        QMessageBox.warning(self, "Error", error)
    
    def update_upload_button(self):
        """Update upload button enabled state"""
        # Check if any items are selected
        selected_count = 0
        for row in range(self.local_items_table.rowCount()):
            checkbox_item = self.local_items_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                selected_count += 1
        
        # Check if destination is valid
        has_destination = False
        if self.same_workspace_radio.isChecked():
            # Check if a workspace is selected
            for row in range(self.local_workspaces_table.rowCount()):
                checkbox_item = self.local_workspaces_table.item(row, 0)
                if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                    has_destination = True
                    break
        elif self.other_workspace_radio.isChecked():
            has_destination = self.fabric_workspace_combo.count() > 0
        
        can_upload = self.authenticated and selected_count > 0 and has_destination
        self.upload_btn.setEnabled(can_upload)
        
        if selected_count > 0:
            self.upload_btn.setText(f" Upload {selected_count} Selected Item{'s' if selected_count != 1 else ''}")
        else:
            self.upload_btn.setText(" Upload Selected Items")
    
    def start_upload(self):
        """Start the upload process"""
        if not self.authenticated or not self.client:
            QMessageBox.warning(self, "Not Authenticated", "Please authenticate first")
            return
        
        # Get selected items
        selected_items = []
        for row in range(self.local_items_table.rowCount()):
            checkbox_item = self.local_items_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                selected_items.append(self.local_items[row])
        
        if not selected_items:
            QMessageBox.warning(self, "No Items", "Please select items to upload")
            return
        
        # Get destination workspace
        workspace_id = None
        workspace_name = None
        
        if self.same_workspace_radio.isChecked():
            # Get selected workspace from local table
            for row in range(self.local_workspaces_table.rowCount()):
                checkbox = self.local_workspaces_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    workspace = self.local_workspaces[row]
                    workspace_name = workspace['name']
                    
                    # Find matching workspace in Fabric by name
                    for fabric_ws in self.fabric_workspaces:
                        if fabric_ws['displayName'] == workspace_name:
                            workspace_id = fabric_ws['id']
                            break
                    
                    if not workspace_id:
                        QMessageBox.warning(self, "Workspace Not Found", 
                            f"Could not find workspace '{workspace_name}' in Fabric.\n\n"
                            "Please select 'Other Workspace' and choose from available workspaces.")
                        return
                    break
        else:
            # Get selected workspace from combo
            workspace_id = self.fabric_workspace_combo.currentData()
            workspace_name = self.fabric_workspace_combo.currentText()
        
        if not workspace_id:
            QMessageBox.warning(self, "No Workspace", "Please select a destination workspace")
            return
        
        # Confirm upload
        reply = QMessageBox.question(
            self,
            "Confirm Upload",
            f"Upload {len(selected_items)} item(s) to workspace '{workspace_name}'?\n\n"
            "Semantic Models will be uploaded first, then Reports.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start upload
        self.log_message(f"Starting upload of {len(selected_items)} items to '{workspace_name}'...")
        self.upload_btn.setEnabled(False)
        self.upload_progress_bar.setVisible(True)
        self.upload_progress_bar.setValue(0)
        self.upload_progress_bar.setMaximum(len(selected_items))
        
        self.upload_worker = FabricUploadWorker(
            self.client, workspace_id, workspace_name, 
            selected_items, self.selected_folder
        )
        self.upload_worker.progress.connect(self.on_upload_progress)
        self.upload_worker.item_complete.connect(self.on_item_uploaded)
        self.upload_worker.finished.connect(self.on_upload_complete)
        self.upload_worker.error.connect(self.on_upload_error)
        self.upload_worker.start()
    
    def on_upload_progress(self, message: str, current: int, total: int):
        """Handle upload progress"""
        self.log_message(message)
        self.upload_progress_bar.setValue(current)
        self.upload_progress_bar.setFormat(f"{current}/{total} - {message}")
    
    def on_item_uploaded(self, item_name: str, success: bool, message: str):
        """Handle individual item upload completion"""
        self.log_message(f"{item_name}: {message}")
    
    def on_upload_complete(self, success_count: int, total_count: int):
        """Handle upload completion"""
        self.upload_progress_bar.setVisible(False)
        self.upload_btn.setEnabled(True)
        
        if success_count == total_count:
            self.log_message(f"✓ Upload complete! {success_count}/{total_count} items uploaded successfully")
            QMessageBox.information(self, "Upload Complete", 
                f"Successfully uploaded {success_count} item(s)!")
        else:
            self.log_message(f"⚠ Upload finished with errors: {success_count}/{total_count} successful")
            QMessageBox.warning(self, "Upload Complete with Errors",
                f"Uploaded {success_count} out of {total_count} items.\n"
                "Check the activity log for details.")
    
    def on_upload_error(self, error: str):
        """Handle upload error"""
        self.log_message(f"❌ Upload error: {error}")
        self.upload_progress_bar.setVisible(False)
        self.upload_btn.setEnabled(True)
        QMessageBox.critical(self, "Upload Error", error)
    
    def apply_upload_button_style(self):
        """Apply theme-aware style to upload button"""
        style = self.theme_manager.get_button_style("primary")
        self.upload_btn.setStyleSheet(style + """
            padding: 10px 20px;
            font-size: 13px;
            border-radius: 5px;
        """)
    
    def apply_theme(self, theme):
        """Apply theme to this tab"""
        self.apply_upload_button_style()
