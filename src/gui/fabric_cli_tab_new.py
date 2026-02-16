"""
Redesigned Fabric CLI Tab - Improved UX with auto-login and better workspace/item selection
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox,
    QGroupBox, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QHeaderView, QCheckBox, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import qtawesome as qta
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from services.fabric_cli_wrapper import FabricCLIWrapper, FabricItem
from utils.theme_manager import get_theme_manager


logger = logging.getLogger(__name__)


class FabricCLIAuthWorker(QThread):
    """Worker thread for auto-login with service principal"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.client = None
    
    def run(self):
        try:
            self.progress.emit("Initializing Fabric CLI...")
            self.client = FabricCLIWrapper()  # Auto-loads from config.md
            
            self.progress.emit("Authenticating with Service Principal...")
            self.client.login(interactive=False)  # Service principal auth
            
            self.finished.emit(True)
        except Exception as e:
            self.error.emit(f"Auto-login failed: {str(e)}")


class FabricCLIWorkspaceWorker(QThread):
    """Worker thread for loading workspaces"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, client: FabricCLIWrapper):
        super().__init__()
        self.client = client
    
    def run(self):
        try:
            self.progress.emit("Loading workspaces...")
            workspaces = self.client.list_workspaces()
            self.finished.emit(workspaces)
        except Exception as e:
            self.error.emit(f"Failed to load workspaces: {str(e)}")


class FabricCLIItemsWorker(QThread):
    """Worker thread for loading workspace items"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, client: FabricCLIWrapper, workspace_id: str):
        super().__init__()
        self.client = client
        self.workspace_id = workspace_id
    
    def run(self):
        try:
            self.progress.emit(f"Loading items from workspace...")
            items = self.client.list_workspace_items(self.workspace_id)
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(f"Failed to load items: {str(e)}")


class FabricCLIDownloadWorker(QThread):
    """Worker thread for downloading multiple items"""
    progress = pyqtSignal(str, int, int)  # message, current, total
    item_complete = pyqtSignal(str, bool, str)  # item_name, success, message
    finished = pyqtSignal(int, int)  # success_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, client: FabricCLIWrapper, workspace_id: str, 
                 items: List[Dict], base_path: str):
        super().__init__()
        self.client = client
        self.workspace_id = workspace_id
        self.items = items
        self.base_path = base_path
    
    def run(self):
        success_count = 0
        total = len(self.items)
        
        try:
            for idx, item in enumerate(self.items, 1):
                try:
                    item_name = item['displayName']
                    item_type = item['type']
                    item_id = item['id']
                    
                    logger.info(f"Processing item {idx}/{total}: {item_name} ({item_type})")
                    
                    # Auto-determine format based on item type
                    if item_type == "Report":
                        format_type = "PBIP"
                    elif item_type == "SemanticModel":
                        format_type = "TMDL"
                    else:
                        format_type = "PBIP"  # Default fallback
                    
                    # Create filename: Name.Type (e.g., Contoso.Report, Contoso.SemanticModel)
                    safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = f"{safe_name}.{item_type}"
                    
                    local_path = Path(self.base_path) / filename
                    
                    self.progress.emit(f"Downloading {filename} as {format_type}...", idx, total)
                    
                    try:
                        result_path = self.client.download_item(
                            workspace_id=self.workspace_id,
                            item_id=item_id,
                            item_type=item_type,
                            local_path=str(local_path),
                            format=format_type
                        )
                        success_count += 1
                        self.item_complete.emit(item_name, True, f"✓ Downloaded {filename} ({format_type}) to {result_path}")
                        logger.info(f"✓ Successfully downloaded {filename}")
                    except Exception as e:
                        logger.error(f"✗ Failed to download {filename}: {e}", exc_info=True)
                        self.item_complete.emit(item_name, False, f"✗ Failed: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Error processing item {idx}: {e}", exc_info=True)
                    self.item_complete.emit(f"Item {idx}", False, f"✗ Error processing item: {str(e)}")
            
            logger.info(f"Download process completed: {success_count}/{total} items successful")
            self.finished.emit(success_count, total)
            
        except Exception as e:
            logger.error(f"Critical error in download worker: {e}", exc_info=True)
            self.error.emit(f"Download process failed: {str(e)}")


class FabricCLITab(QWidget):
    """Redesigned Fabric CLI Tab with improved UX"""
    
    # Signal emitted when download completes successfully
    download_complete_signal = pyqtSignal()
    
    def __init__(self, downloads_base: Path, parent=None):
        super().__init__(parent)
        self.downloads_base = downloads_base
        self.client: Optional[FabricCLIWrapper] = None
        self.authenticated = False
        self.workspaces = []
        self.current_workspace_id = None
        self.current_workspace_name = None
        self.current_items = []
        self.export_folder = None  # Will be created on first download
        self.theme_manager = get_theme_manager()
        self.init_ui()
        
        # Auto-login on startup
        self.auto_login()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Header with status and info on same line
        header_layout = QHBoxLayout()
        header = QLabel("🌐 Microsoft Fabric CLI")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(header)
        
        # Login status in header
        self.login_status = QLabel("⏳ Connecting...")
        self.login_status.setStyleSheet("color: orange; font-weight: bold;")
        header_layout.addWidget(self.login_status)
        
        # Add info message in header
        info_label = QLabel("  |  ℹ️ Reports → PBIP, Semantic Models → TMDL")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(info_label)
        
        header_layout.addStretch()
        
        self.login_btn = QPushButton(qta.icon('fa5s.redo'), " Retry Login")
        self.login_btn.setVisible(False)
        self.login_btn.clicked.connect(self.auto_login)
        header_layout.addWidget(self.login_btn)
        
        layout.addLayout(header_layout)
        
        # Create splitter for side-by-side layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT SIDE: Workspaces section
        workspace_widget = QWidget()
        workspace_main_layout = QVBoxLayout(workspace_widget)
        workspace_main_layout.setContentsMargins(0, 0, 0, 0)
        
        workspace_group = QGroupBox("1️⃣ Select Workspace")
        workspace_layout = QVBoxLayout()
        
        ws_controls = QHBoxLayout()
        self.refresh_ws_btn = QPushButton(qta.icon('fa5s.sync'), " Refresh")
        self.refresh_ws_btn.clicked.connect(self.load_workspaces)
        self.refresh_ws_btn.setEnabled(False)
        ws_controls.addWidget(self.refresh_ws_btn)
        ws_controls.addStretch()
        workspace_layout.addLayout(ws_controls)
        
        # Workspaces table with checkbox
        self.workspaces_table = QTableWidget()
        self.workspaces_table.setColumnCount(2)
        self.workspaces_table.setHorizontalHeaderLabels(["Select", "Workspace Name"])
        self.workspaces_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.workspaces_table.setColumnWidth(0, 60)
        self.workspaces_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.workspaces_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        workspace_layout.addWidget(self.workspaces_table)
        
        workspace_group.setLayout(workspace_layout)
        workspace_main_layout.addWidget(workspace_group)
        
        splitter.addWidget(workspace_widget)
        
        # RIGHT SIDE: Items section
        items_widget = QWidget()
        items_main_layout = QVBoxLayout(items_widget)
        items_main_layout.setContentsMargins(0, 0, 0, 0)
        
        items_group = QGroupBox("2️⃣ Select Items to Download")
        items_layout = QVBoxLayout()
        
        items_controls = QHBoxLayout()
        items_controls.addWidget(QLabel("Selected workspace items:"))
        
        self.select_all_btn = QPushButton(qta.icon('fa5s.check-square'), "Select All")
        self.select_all_btn.clicked.connect(self.select_all_items)
        items_controls.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton(qta.icon('fa5s.square'), "Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        items_controls.addWidget(self.deselect_all_btn)
        
        items_controls.addStretch()
        items_layout.addLayout(items_controls)
        
        # Items table with checkbox in first column
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["Select", "Name", "Type"])
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.items_table.setColumnWidth(0, 60)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.items_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.items_table.itemChanged.connect(self.on_item_checkbox_changed)
        items_layout.addWidget(self.items_table)
        
        items_group.setLayout(items_layout)
        items_main_layout.addWidget(items_group)
        
        splitter.addWidget(items_widget)
        
        # Set splitter sizes (40% workspaces, 60% items)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter, 1)  # Give splitter stretch factor to fill space
        
        # Download section - all on one line
        download_group = QGroupBox("3️⃣ Download Options")
        download_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        download_layout = QVBoxLayout()
        download_layout.setContentsMargins(5, 5, 5, 5)
        
        # Single line with all controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Base folder:"))
        self.download_path_label = QLabel(str(self.downloads_base))
        self.download_path_label.setStyleSheet("color: #0078D4; font-size: 11px;")
        controls_layout.addWidget(self.download_path_label)
        
        self.browse_btn = QPushButton(qta.icon('fa5s.folder-open'), " Browse")
        self.browse_btn.clicked.connect(self.browse_download_path)
        self.browse_btn.setMaximumWidth(100)
        controls_layout.addWidget(self.browse_btn)
        
        controls_layout.addStretch()
        
        # Download button on the right
        self.download_btn = QPushButton(qta.icon('fa5s.download'), " Download Selected Items")
        self.apply_download_button_style()
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setEnabled(False)
        controls_layout.addWidget(self.download_btn)
        
        download_layout.addLayout(controls_layout)
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Log output - fixed height to prevent expansion
        log_group = QGroupBox("📋 Activity Log")
        log_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(5, 5, 5, 5)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(120)
        self.log_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
    
    def log(self, message: str):
        """Add message to log output (newest first)"""
        # Insert at the beginning instead of appending
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertText(f"{message}\n")
        self.log_output.setTextCursor(cursor)
        logger.info(message)
    
    def auto_login(self):
        """Automatically login with service principal from config.md"""
        self.log("🔐 Starting automatic authentication from config.md...")
        self.login_status.setText("⏳ Authenticating...")
        self.login_status.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
        self.login_btn.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        self.auth_worker = FabricCLIAuthWorker()
        self.auth_worker.progress.connect(self.log)
        self.auth_worker.finished.connect(self.on_auth_complete)
        self.auth_worker.error.connect(self.on_auth_error)
        self.auth_worker.start()
    
    def on_auth_complete(self, success: bool):
        """Handle authentication completion"""
        self.progress_bar.setVisible(False)
        if success:
            self.client = self.auth_worker.client
            self.authenticated = True
            self.login_status.setText("✅ Connected")
            self.login_status.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.refresh_ws_btn.setEnabled(True)
            self.log("✅ Successfully authenticated to Microsoft Fabric!")
            
            # Auto-load workspaces
            self.load_workspaces()
    
    def on_auth_error(self, error: str):
        """Handle authentication error"""
        self.progress_bar.setVisible(False)
        self.login_status.setText("❌ Connection Failed")
        self.login_status.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        self.login_btn.setVisible(True)
        self.log(f"❌ Authentication failed: {error}")
        QMessageBox.critical(self, "Authentication Failed", 
                           f"Failed to connect to Microsoft Fabric:\n\n{error}\n\n"
                           "Please check your config.md file has valid credentials.")
    
    def load_workspaces(self):
        """Load workspaces"""
        if not self.authenticated:
            return
        
        self.log("📂 Loading workspaces...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.ws_worker = FabricCLIWorkspaceWorker(self.client)
        self.ws_worker.progress.connect(self.log)
        self.ws_worker.finished.connect(self.on_workspaces_loaded)
        self.ws_worker.error.connect(self.on_workspaces_error)
        self.ws_worker.start()
    
    def on_workspaces_loaded(self, workspaces: list):
        """Handle workspaces loaded"""
        self.progress_bar.setVisible(False)
        self.workspaces = workspaces
        self.log(f"✅ Loaded {len(workspaces)} workspaces")
        
        # Populate workspaces table
        self.workspaces_table.setRowCount(len(workspaces))
        for row, ws in enumerate(workspaces):
            # Checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            self.workspaces_table.setItem(row, 0, checkbox_item)
            
            # Workspace name
            name_item = QTableWidgetItem(ws['displayName'])
            name_item.setData(Qt.ItemDataRole.UserRole, ws['id'])
            self.workspaces_table.setItem(row, 1, name_item)
        
        self.workspaces_table.itemChanged.connect(self.on_workspace_checkbox_changed)
    
    def on_workspaces_error(self, error: str):
        """Handle workspace loading error"""
        self.progress_bar.setVisible(False)
        self.log(f"❌ Failed to load workspaces: {error}")
        QMessageBox.warning(self, "Error", f"Failed to load workspaces:\n{error}")
    
    def on_workspace_checkbox_changed(self, item: QTableWidgetItem):
        """Handle workspace checkbox change - only allow single selection"""
        if item.column() == 0 and item.checkState() == Qt.CheckState.Checked:
            # Uncheck all other workspaces
            for row in range(self.workspaces_table.rowCount()):
                if row != item.row():
                    self.workspaces_table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)
            
            # Get selected workspace
            workspace_name = self.workspaces_table.item(item.row(), 1).text()
            workspace_id = self.workspaces_table.item(item.row(), 1).data(Qt.ItemDataRole.UserRole)
            self.current_workspace_id = workspace_id
            self.current_workspace_name = workspace_name
            
            self.log(f"📂 Selected workspace: {workspace_name}")
            self.load_items(workspace_id)
        elif item.column() == 0 and item.checkState() == Qt.CheckState.Unchecked:
            # If unchecked, clear items
            if self.current_workspace_id == self.workspaces_table.item(item.row(), 1).data(Qt.ItemDataRole.UserRole):
                self.items_table.setRowCount(0)
                self.current_items = []
                self.current_workspace_id = None
                self.current_workspace_name = None
                self.download_btn.setEnabled(False)
    
    def load_items(self, workspace_id: str):
        """Load items for selected workspace"""
        self.log("📋 Loading workspace items...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.items_worker = FabricCLIItemsWorker(self.client, workspace_id)
        self.items_worker.progress.connect(self.log)
        self.items_worker.finished.connect(self.on_items_loaded)
        self.items_worker.error.connect(self.on_items_error)
        self.items_worker.start()
    
    def on_items_loaded(self, items: list):
        """Handle items loaded"""
        self.progress_bar.setVisible(False)
        
        # Convert FabricItem objects to dicts for easier handling
        self.current_items = []
        for item in items:
            if hasattr(item, 'id'):  # FabricItem object
                item_dict = {
                    'id': item.id,
                    'displayName': item.name,
                    'type': item.type,
                    'workspaceId': item.workspace_id
                }
            else:  # Already a dict
                item_dict = item
            self.current_items.append(item_dict)
        
        self.log(f"✅ Loaded {len(self.current_items)} items")
        
        # Disconnect to prevent triggering during population
        try:
            self.items_table.itemChanged.disconnect(self.on_item_checkbox_changed)
        except:
            pass
        
        # Populate items table
        self.items_table.setRowCount(len(self.current_items))
        for row, item in enumerate(self.current_items):
            # Checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            self.items_table.setItem(row, 0, checkbox_item)
            
            # Name
            name_item = QTableWidgetItem(item['displayName'])
            name_item.setData(Qt.ItemDataRole.UserRole, item)
            self.items_table.setItem(row, 1, name_item)
            
            # Type
            type_item = QTableWidgetItem(item['type'])
            self.items_table.setItem(row, 2, type_item)
        
        # Reconnect
        self.items_table.itemChanged.connect(self.on_item_checkbox_changed)
        self.download_btn.setEnabled(False)
    
    def on_items_error(self, error: str):
        """Handle items loading error"""
        self.progress_bar.setVisible(False)
        self.log(f"❌ Failed to load items: {error}")
        QMessageBox.warning(self, "Error", f"Failed to load items:\n{error}")
    
    def on_item_checkbox_changed(self, item: QTableWidgetItem):
        """Handle item checkbox change - auto-select related items"""
        if item.column() != 0:
            return
        
        # Disconnect to prevent recursion
        try:
            self.items_table.itemChanged.disconnect(self.on_item_checkbox_changed)
        except:
            pass
        
        row = item.row()
        is_checked = item.checkState() == Qt.CheckState.Checked
        
        if is_checked:
            # Get the item data
            item_data = self.items_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            item_name = item_data['displayName']
            
            # Auto-select related items with the same name but different type
            for check_row in range(self.items_table.rowCount()):
                if check_row != row:
                    check_item_data = self.items_table.item(check_row, 1).data(Qt.ItemDataRole.UserRole)
                    if check_item_data['displayName'] == item_name:
                        self.items_table.item(check_row, 0).setCheckState(Qt.CheckState.Checked)
                        self.log(f"✓ Auto-selected related item: {item_name} ({check_item_data['type']})")
        
        # Reconnect
        self.items_table.itemChanged.connect(self.on_item_checkbox_changed)
        
        # Enable/disable download button
        self.update_download_button()
    
    def update_download_button(self):
        """Update download button state based on selection"""
        selected_count = sum(
            1 for row in range(self.items_table.rowCount())
            if self.items_table.item(row, 0).checkState() == Qt.CheckState.Checked
        )
        self.download_btn.setEnabled(selected_count > 0)
        if selected_count > 0:
            self.download_btn.setText(f"📥 Download {selected_count} Selected Item{'s' if selected_count > 1 else ''}")
        else:
            self.download_btn.setText("📥 Download Selected Items")
    
    def select_all_items(self):
        """Select all items"""
        try:
            self.items_table.itemChanged.disconnect(self.on_item_checkbox_changed)
        except:
            pass
        
        for row in range(self.items_table.rowCount()):
            self.items_table.item(row, 0).setCheckState(Qt.CheckState.Checked)
        
        self.items_table.itemChanged.connect(self.on_item_checkbox_changed)
        self.update_download_button()
        self.log("✓ Selected all items")
    
    def deselect_all_items(self):
        """Deselect all items"""
        try:
            self.items_table.itemChanged.disconnect(self.on_item_checkbox_changed)
        except:
            pass
        
        for row in range(self.items_table.rowCount()):
            self.items_table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)
        
        self.items_table.itemChanged.connect(self.on_item_checkbox_changed)
        self.update_download_button()
        self.log("✓ Deselected all items")
    
    def browse_download_path(self):
        """Browse for download path"""
        path = QFileDialog.getExistingDirectory(self, "Select Download Folder", str(self.downloads_base))
        if path:
            self.downloads_base = Path(path)
            self.download_path_label.setText(str(self.downloads_base))
            self.log(f"📁 Download path changed to: {path}")
    
    def download_selected(self):
        """Download selected items"""
        try:
            if not self.authenticated or not self.current_workspace_id or not self.current_workspace_name:
                logger.warning("Cannot download: Not authenticated or no workspace selected")
                return
            
            # Get selected items
            selected_items = []
            for row in range(self.items_table.rowCount()):
                if self.items_table.item(row, 0).checkState() == Qt.CheckState.Checked:
                    item_data = self.items_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                    selected_items.append(item_data)
            
            if not selected_items:
                QMessageBox.warning(self, "No Selection", "Please select at least one item to download.")
                return
            
            logger.info(f"Starting download of {len(selected_items)} items")
            
            # Create folder structure: base/FabricExport_{timestamp}/Raw Files/{workspace_name}/
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            export_folder_name = f"FabricExport_{timestamp}"
            self.export_folder = self.downloads_base / export_folder_name / "Raw Files" / self.current_workspace_name
            self.export_folder.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Export folder: {self.export_folder}")
            
            self.log(f"📥 Starting download of {len(selected_items)} items...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(len(selected_items))
            self.download_btn.setEnabled(False)
            
            self.download_worker = FabricCLIDownloadWorker(
                self.client, 
                self.current_workspace_id,
                selected_items,
                str(self.export_folder)  # Pass the full export folder path
            )
            self.download_worker.progress.connect(self.on_download_progress)
            self.download_worker.item_complete.connect(self.on_item_downloaded)
            self.download_worker.finished.connect(self.on_download_complete)
            self.download_worker.error.connect(self.on_download_error)
            
            logger.info("Starting download worker thread...")
            self.download_worker.start()
            
        except Exception as e:
            logger.error(f"Error in download_selected: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to start download:\n{str(e)}")
            self.download_btn.setEnabled(True)
    
    def on_download_progress(self, message: str, current: int, total: int):
        """Handle download progress"""
        self.progress_bar.setValue(current - 1)
        self.log(f"[{current}/{total}] {message}")
    
    def on_item_downloaded(self, item_name: str, success: bool, message: str):
        """Handle individual item download completion"""
        self.log(message)
    
    def on_download_complete(self, success_count: int, total_count: int):
        """Handle download completion"""
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        
        if success_count == total_count:
            self.log(f"✅ Successfully downloaded all {total_count} items!")
            QMessageBox.information(self, "Success", 
                                  f"Successfully downloaded {success_count} items to:\n{self.export_folder}")
            # Emit signal to refresh Assessment tab dropdown
            self.download_complete_signal.emit()
        else:
            self.log(f"⚠️ Downloaded {success_count}/{total_count} items (some failed)")
            QMessageBox.warning(self, "Partial Success", 
                              f"Downloaded {success_count} out of {total_count} items.\n"
                              f"Check the log for details.")
            # Still emit signal even for partial success to refresh Assessment dropdown
            if success_count > 0:
                self.download_complete_signal.emit()
    
    def on_download_error(self, error: str):
        """Handle download error"""
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.log(f"❌ Download failed: {error}")
        QMessageBox.critical(self, "Download Failed", f"Download process failed:\n{error}")
    
    def apply_download_button_style(self):
        """Apply theme-aware style to download button"""
        style = self.theme_manager.get_button_style("primary")
        self.download_btn.setStyleSheet(style + """
            padding: 10px 20px;
            font-size: 13px;
            border-radius: 5px;
        """)
    
    def apply_theme(self, theme):
        """Apply theme to this tab"""
        self.apply_download_button_style()
        
        # Update header colors
        color = self.theme_manager.get_text_color("secondary")
        for child in self.findChildren(QLabel):
            if "Reports → PBIP" in child.text():
                child.setStyleSheet(f"color: {color}; font-size: 11px;")
