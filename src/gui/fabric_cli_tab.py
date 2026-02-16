"""
Integration module for Fabric CLI Wrapper in existing PyQt6 GUI
This adds a new tab to the main window for Fabric CLI functionality
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTableWidget, QTableWidgetItem, QComboBox,
    QGroupBox, QFormLayout, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QHeaderView, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import qtawesome as qta
import logging
from pathlib import Path
from typing import Optional

from services.fabric_cli_wrapper import FabricCLIWrapper, FabricItem


logger = logging.getLogger(__name__)


class FabricCLIAuthWorker(QThread):
    """Worker thread for Fabric CLI authentication"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def __init__(self, tenant_id=None, client_id=None, client_secret=None, interactive=True):
        super().__init__()
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.interactive = interactive
        self.client = None
    
    def run(self):
        try:
            self.progress.emit("Initializing Fabric CLI client...")
            
            self.client = FabricCLIWrapper(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            self.progress.emit("Authenticating...")
            self.client.login(interactive=self.interactive)
            
            self.finished.emit(True)
        except ImportError as e:
            self.error.emit(f"Fabric CLI not installed: {str(e)}\n\nInstall with: pip install ms-fabric-cli")
        except Exception as e:
            self.error.emit(f"Authentication failed: {str(e)}")


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
            self.progress.emit(f"Loading items from workspace {self.workspace_id}...")
            items = self.client.list_workspace_items(self.workspace_id)
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(f"Failed to load items: {str(e)}")


class FabricCLIDownloadWorker(QThread):
    """Worker thread for downloading items"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, client: FabricCLIWrapper, workspace_id: str, 
                 item_id: str, item_type: str, local_path: str, format: str):
        super().__init__()
        self.client = client
        self.workspace_id = workspace_id
        self.item_id = item_id
        self.item_type = item_type
        self.local_path = local_path
        self.format = format
    
    def run(self):
        try:
            self.progress.emit(f"Downloading {self.item_type}...")
            result_path = self.client.download_item(
                workspace_id=self.workspace_id,
                item_id=self.item_id,
                item_type=self.item_type,
                local_path=self.local_path,
                format=self.format
            )
            self.finished.emit(str(result_path))
        except Exception as e:
            self.error.emit(f"Download failed: {str(e)}")


class FabricCLITab(QWidget):
    """Tab widget for Fabric CLI functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: Optional[FabricCLIWrapper] = None
        self.authenticated = False
        self.workspaces = []
        self.current_items = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Microsoft Fabric CLI - Python API")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D4;")
        layout.addWidget(header)
        
        info = QLabel("Direct Python integration with Fabric CLI - No PowerShell required")
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Authentication section
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()
        
        # Auth method selection
        auth_method_layout = QHBoxLayout()
        self.interactive_radio = QCheckBox("Interactive Browser")
        self.interactive_radio.setChecked(True)
        self.interactive_radio.toggled.connect(self.on_auth_method_changed)
        auth_method_layout.addWidget(self.interactive_radio)
        
        self.sp_radio = QCheckBox("Service Principal")
        self.sp_radio.toggled.connect(self.on_auth_method_changed)
        auth_method_layout.addWidget(self.sp_radio)
        auth_method_layout.addStretch()
        
        auth_layout.addRow("Method:", auth_method_layout)
        
        # Service principal fields
        self.tenant_id_input = QLineEdit()
        self.tenant_id_input.setPlaceholderText("Azure AD Tenant ID")
        self.tenant_id_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.tenant_id_input.setEnabled(False)
        auth_layout.addRow("Tenant ID:", self.tenant_id_input)
        
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Service Principal Client ID")
        self.client_id_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_id_input.setEnabled(False)
        auth_layout.addRow("Client ID:", self.client_id_input)
        
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("Service Principal Secret")
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_input.setEnabled(False)
        auth_layout.addRow("Client Secret:", self.client_secret_input)
        
        # Login button
        login_layout = QHBoxLayout()
        self.login_btn = QPushButton(qta.icon('fa5s.sign-in-alt'), " Login")
        self.login_btn.clicked.connect(self.authenticate)
        login_layout.addWidget(self.login_btn)
        
        self.auth_status = QLabel("Not authenticated")
        self.auth_status.setStyleSheet("color: red;")
        login_layout.addWidget(self.auth_status)
        login_layout.addStretch()
        
        auth_layout.addRow(login_layout)
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # Workspace section
        workspace_group = QGroupBox("Workspaces")
        workspace_layout = QVBoxLayout()
        
        ws_controls = QHBoxLayout()
        self.refresh_ws_btn = QPushButton(qta.icon('fa5s.sync'), " Refresh Workspaces")
        self.refresh_ws_btn.clicked.connect(self.load_workspaces)
        self.refresh_ws_btn.setEnabled(False)
        ws_controls.addWidget(self.refresh_ws_btn)
        
        ws_controls.addWidget(QLabel("Select:"))
        self.workspace_combo = QComboBox()
        self.workspace_combo.currentIndexChanged.connect(self.on_workspace_selected)
        self.workspace_combo.setEnabled(False)
        ws_controls.addWidget(self.workspace_combo, 1)
        
        workspace_layout.addLayout(ws_controls)
        workspace_group.setLayout(workspace_layout)
        layout.addWidget(workspace_group)
        
        # Items section
        items_group = QGroupBox("Workspace Items")
        items_layout = QVBoxLayout()
        
        items_controls = QHBoxLayout()
        self.load_items_btn = QPushButton(qta.icon('fa5s.list'), " Load Items")
        self.load_items_btn.clicked.connect(self.load_items)
        self.load_items_btn.setEnabled(False)
        items_controls.addWidget(self.load_items_btn)
        
        items_controls.addWidget(QLabel("Filter:"))
        self.item_filter_combo = QComboBox()
        self.item_filter_combo.addItems(["All", "SemanticModel", "Report", "Dashboard"])
        self.item_filter_combo.currentTextChanged.connect(self.apply_item_filter)
        items_controls.addWidget(self.item_filter_combo)
        items_controls.addStretch()
        
        items_layout.addLayout(items_controls)
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.items_table.setHorizontalHeaderLabels(["Name", "Type", "ID"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        items_layout.addWidget(self.items_table)
        
        # Download controls
        download_controls = QHBoxLayout()
        download_controls.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["TMDL", "PBIP"])
        download_controls.addWidget(self.format_combo)
        
        self.download_btn = QPushButton(qta.icon('fa5s.download'), " Download Selected")
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setEnabled(False)
        download_controls.addWidget(self.download_btn)
        download_controls.addStretch()
        
        items_layout.addLayout(download_controls)
        items_group.setLayout(items_layout)
        layout.addWidget(items_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log output
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
    
    def on_auth_method_changed(self):
        """Handle auth method radio button changes"""
        is_sp = self.sp_radio.isChecked()
        self.tenant_id_input.setEnabled(is_sp)
        self.client_id_input.setEnabled(is_sp)
        self.client_secret_input.setEnabled(is_sp)
        
        if is_sp:
            self.interactive_radio.setChecked(False)
        else:
            self.interactive_radio.setChecked(True)
    
    def log(self, message: str):
        """Add message to log output"""
        self.log_output.append(message)
        logger.info(message)
    
    def authenticate(self):
        """Authenticate to Fabric"""
        self.log("Starting authentication...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        interactive = self.interactive_radio.isChecked()
        tenant_id = self.tenant_id_input.text() if not interactive else None
        client_id = self.client_id_input.text() if not interactive else None
        client_secret = self.client_secret_input.text() if not interactive else None
        
        self.auth_worker = FabricCLIAuthWorker(tenant_id, client_id, client_secret, interactive)
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
            self.auth_status.setText("✓ Authenticated")
            self.auth_status.setStyleSheet("color: green;")
            self.login_btn.setEnabled(False)
            self.refresh_ws_btn.setEnabled(True)
            self.workspace_combo.setEnabled(True)
            self.load_items_btn.setEnabled(True)
            self.download_btn.setEnabled(True)
            self.log("✓ Successfully authenticated!")
            QMessageBox.information(self, "Success", "Successfully authenticated to Microsoft Fabric!")
    
    def on_auth_error(self, error: str):
        """Handle authentication error"""
        self.progress_bar.setVisible(False)
        self.log(f"✗ Authentication failed: {error}")
        QMessageBox.critical(self, "Authentication Failed", error)
    
    def load_workspaces(self):
        """Load workspaces"""
        if not self.authenticated:
            return
        
        self.log("Loading workspaces...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.ws_worker = FabricCLIWorkspaceWorker(self.client)
        self.ws_worker.progress.connect(self.log)
        self.ws_worker.finished.connect(self.on_workspaces_loaded)
        self.ws_worker.error.connect(self.on_load_error)
        self.ws_worker.start()
    
    def on_workspaces_loaded(self, workspaces: list):
        """Handle workspaces loaded"""
        self.progress_bar.setVisible(False)
        self.workspaces = workspaces
        self.workspace_combo.clear()
        
        for ws in workspaces:
            name = ws.get('displayName', ws.get('name', 'Unnamed'))
            self.workspace_combo.addItem(f"{name}", ws['id'])
        
        self.log(f"✓ Loaded {len(workspaces)} workspaces")
    
    def on_workspace_selected(self, index: int):
        """Handle workspace selection"""
        if index >= 0:
            ws_id = self.workspace_combo.itemData(index)
            self.log(f"Selected workspace: {self.workspace_combo.currentText()}")
    
    def load_items(self):
        """Load items from selected workspace"""
        if not self.authenticated or self.workspace_combo.currentIndex() < 0:
            return
        
        workspace_id = self.workspace_combo.currentData()
        self.log(f"Loading items from workspace...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.items_worker = FabricCLIItemsWorker(self.client, workspace_id)
        self.items_worker.progress.connect(self.log)
        self.items_worker.finished.connect(self.on_items_loaded)
        self.items_worker.error.connect(self.on_load_error)
        self.items_worker.start()
    
    def on_items_loaded(self, items: list):
        """Handle items loaded"""
        self.progress_bar.setVisible(False)
        self.current_items = items
        self.apply_item_filter()
        self.log(f"✓ Loaded {len(items)} items")
    
    def apply_item_filter(self):
        """Apply filter to items table"""
        self.items_table.setRowCount(0)
        
        filter_type = self.item_filter_combo.currentText()
        filtered_items = self.current_items if filter_type == "All" else [
            item for item in self.current_items if item.type == filter_type
        ]
        
        for item in filtered_items:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            self.items_table.setItem(row, 0, QTableWidgetItem(item.name))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.type))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.id))
    
    def download_selected(self):
        """Download selected item"""
        selected_rows = self.items_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an item to download")
            return
        
        row = self.items_table.currentRow()
        item_name = self.items_table.item(row, 0).text()
        item_type = self.items_table.item(row, 1).text()
        item_id = self.items_table.item(row, 2).text()
        
        # Find the full item
        item = next((i for i in self.current_items if i.id == item_id), None)
        if not item:
            return
        
        # Ask for save location
        format_ext = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            f"{item_name}.{format_ext}",
            f"{format_ext.upper()} files (*.{format_ext});;All files (*.*)"
        )
        
        if not file_path:
            return
        
        self.log(f"Downloading {item_name}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.download_worker = FabricCLIDownloadWorker(
            self.client, item.workspace_id, item.id, item.type,
            file_path, self.format_combo.currentText()
        )
        self.download_worker.progress.connect(self.log)
        self.download_worker.finished.connect(self.on_download_complete)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.start()
    
    def on_download_complete(self, path: str):
        """Handle download completion"""
        self.progress_bar.setVisible(False)
        self.log(f"✓ Downloaded to {path}")
        QMessageBox.information(self, "Success", f"Successfully downloaded to:\n{path}")
    
    def on_download_error(self, error: str):
        """Handle download error"""
        self.progress_bar.setVisible(False)
        self.log(f"✗ Download failed: {error}")
        QMessageBox.critical(self, "Download Failed", error)
    
    def on_load_error(self, error: str):
        """Handle load error"""
        self.progress_bar.setVisible(False)
        self.log(f"✗ Error: {error}")
        QMessageBox.critical(self, "Error", error)
