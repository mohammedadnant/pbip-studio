"""
Main Window for Power BI Migration Toolkit
PyQt6 GUI with tabbed interface
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QComboBox, QTextEdit,
    QSplitter, QGroupBox, QFormLayout, QCheckBox, QHeaderView, QGridLayout,
    QTreeWidget, QTreeWidgetItem, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap
from PyQt6.QtWidgets import QApplication
import qtawesome as qta
import requests
import logging
from pathlib import Path
from datetime import datetime
import json
import os
import sys
import subprocess
import re
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from data_source_migration import detect_data_sources, generate_new_m_query, migrate_all_tables, DATA_SOURCE_TEMPLATES, scan_backups, restore_from_backup, preview_migration
from table_rename import get_tables_from_model, rename_tables_bulk
from column_rename import (
    get_columns_from_table, apply_column_transformation, rename_columns_bulk
)
from services.fabric_client import FabricClient, FabricConfig, FabricAPIError, load_config_from_file
from gui.fabric_cli_tab_new import FabricCLITab
from gui.fabric_upload_tab import FabricUploadTab
from gui.widgets.preview_dialog import PreviewDialog
from gui.widgets.side_by_side_diff import SideBySideDiffViewer
from database.schema import FabricDatabase
from services.indexer import IndexingService
from utils.theme_manager import get_theme_manager

class IndexWorker(QThread):
    """Worker thread for indexing operations - Direct service call (no HTTP)"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    file_info = pyqtSignal(dict)  # New signal for file structure info
    
    def __init__(self, export_path, tool_id="powerbi"):
        super().__init__()
        self.export_path = export_path
        self.tool_id = tool_id
        
    def run(self):
        try:
            self.progress.emit("Initializing database...")
            # Direct service call - no HTTP overhead!
            db = FabricDatabase()
            indexer = IndexingService(db)
            
            export_path_obj = Path(self.export_path)
            
            # Collect file structure info
            self.progress.emit("Scanning file structure...")
            file_structure = self._scan_structure(export_path_obj)
            self.file_info.emit(file_structure)
            
            # Run indexing
            self.progress.emit("Parsing TMDL files and extracting metadata...")
            stats = indexer.index_export_folder(export_path_obj, tool_id=self.tool_id)
            
            # Add file structure to stats
            stats['file_structure'] = file_structure
            self.finished.emit(stats)
            
        except Exception as e:
            logging.error(f"Indexing error: {e}", exc_info=True)
            self.error.emit(str(e))
    
    def _scan_structure(self, export_path):
        """Scan and return file structure information"""
        structure = {
            'root': str(export_path),
            'workspaces': [],
            'total_tmdl_files': 0,
            'total_size_mb': 0
        }
        
        # Find workspace root
        if (export_path / "Raw Files").exists():
            workspace_root = export_path / "Raw Files"
        elif (export_path / "Processed_Data").exists():
            workspace_root = export_path / "Processed_Data"
        else:
            workspace_root = export_path
        
        total_size = 0
        
        for ws_folder in workspace_root.iterdir():
            if not ws_folder.is_dir():
                continue
                
            ws_info = {
                'name': ws_folder.name,
                'path': str(ws_folder),
                'datasets': []
            }
            
            for item_folder in ws_folder.glob("*.SemanticModel"):
                dataset_info = {
                    'name': item_folder.name.replace('.SemanticModel', ''),
                    'path': str(item_folder),
                    'tables': [],
                    'tmdl_files': 0,
                    'size_mb': 0
                }
                
                # Count TMDL files and size
                tmdl_files = list(item_folder.rglob("*.tmdl"))
                dataset_info['tmdl_files'] = len(tmdl_files)
                structure['total_tmdl_files'] += len(tmdl_files)
                
                dataset_size = sum(f.stat().st_size for f in item_folder.rglob('*') if f.is_file())
                dataset_info['size_mb'] = round(dataset_size / (1024 * 1024), 2)
                total_size += dataset_size
                
                # List table files
                tables_path = item_folder / "definition" / "tables"
                if tables_path.exists():
                    dataset_info['tables'] = [t.stem for t in tables_path.glob("*.tmdl")]
                
                ws_info['datasets'].append(dataset_info)
            
            if ws_info['datasets']:  # Only add if has datasets
                structure['workspaces'].append(ws_info)
        
        structure['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        return structure


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        logging.info("Initializing MainWindow")
        self.api_base = "http://127.0.0.1:8000"
        
        # Initialize theme manager
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        
        # Centralized app data directory in LOCALAPPDATA (user-writable, not Program Files)
        self.app_data_dir = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'PowerBI Migration Toolkit'
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"App data directory: {self.app_data_dir}")
        
        # Downloads folder is now in user's Documents, not Program Files
        documents_folder = Path(os.path.expanduser("~/Documents"))
        self.downloads_base = documents_folder / "PowerBI-Toolkit-Downloads"
        logging.info(f"Downloads base: {self.downloads_base}")
        
        logging.info("Starting init_ui")
        self.init_ui()
        logging.info("init_ui completed")
        # Auto-scan Downloads folder after UI is ready
        QTimer.singleShot(500, self.auto_scan_downloads)
        # Check API health after a delay
        QTimer.singleShot(1000, self.check_api_health)
        logging.info("MainWindow initialization complete")
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("PBIP Studio")
        
        # Set window icon - try transparent PNG first, fallback to ICO
        logo_path = self.theme_manager.get_logo_path(32)
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        else:
            # Fallback to ICO file
            icon_path = Path(__file__).parent.parent.parent / "pbip-studio.ico"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        
        # Apply theme stylesheet
        self.apply_theme()
        
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Header
        self.create_header(layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)
        
        # Add tabs
        self.create_configuration_tab()
        # Add Download from Fabric tab (Python API - no PowerShell)
        self.fabric_cli_tab = FabricCLITab(downloads_base=self.downloads_base)
        self.tabs.addTab(self.fabric_cli_tab, qta.icon('fa5s.cloud-download-alt', color=self._get_tab_icon_color()), "Download from Fabric")
        self.create_assessment_tab()
        # Connect download completion to refresh assessment dropdown
        self.fabric_cli_tab.download_complete_signal.connect(self.refresh_assessment_dropdown)
        self.create_migration_tab()
        self.create_preview_tab()  # Add preview tab
        self.create_rename_tab()
        self.create_column_rename_tab()
        # Add Upload to Fabric tab
        self.fabric_upload_tab = FabricUploadTab(downloads_base=self.downloads_base)
        self.tabs.addTab(self.fabric_upload_tab, qta.icon('fa5s.cloud-upload-alt', color=self._get_tab_icon_color()), "Upload to Fabric")
        self.create_restore_tab()
        
        # Footer with copyright
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 5, 10, 5)
        
        # Left side - backup count info
        self.backup_count_label = QLabel("Found 4 backup(s)")
        self.backup_count_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        footer_layout.addWidget(self.backup_count_label)
        
        footer_layout.addStretch()
        
        # Right side - copyright
        copyright_label = QLabel("© 2024-2026 Taik18 | Powered by Taik18")
        copyright_label.setStyleSheet("color: #95a5a6; font-size: 10px; font-style: italic;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        footer_layout.addWidget(copyright_label)
        
        layout.addWidget(footer)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_header(self, layout):
        """Create application header"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        
        # Logo
        self.header_logo_label = QLabel()
        self._update_header_logo()
        header_layout.addWidget(self.header_logo_label)
        
        # Title
        title = QLabel("PBIP Studio")
        title_font = QFont("Arial", 20, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #0078D4; margin-left: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Theme toggle button
        self.theme_toggle_btn = QPushButton()
        self.update_theme_icon()
        self.theme_toggle_btn.setFixedSize(40, 40)
        self.theme_toggle_btn.setToolTip("Toggle Light/Dark Mode")
        self.theme_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 212, 0.2);
            }
        """)
        self.theme_toggle_btn.setIconSize(QSize(22, 22))
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_toggle_btn)
        
        # Help icon button
        help_btn = QPushButton(qta.icon('fa5s.question-circle', color='#0078D4'), "")
        help_btn.setFixedSize(40, 40)
        help_btn.setToolTip("Open User Guide")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 212, 0.2);
            }
        """)
        help_btn.setIconSize(QSize(24, 24))
        help_btn.clicked.connect(self.open_user_guide)
        header_layout.addWidget(help_btn)
        
        layout.addWidget(header)
    
    def create_configuration_tab(self):
        """Create Configuration tab for Fabric credentials"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Header with info inline
        header_layout = QHBoxLayout()
        
        info_label = QLabel("⚙️ Fabric API Configuration")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(info_label)
        
        # Config location in header
        config_location = self.app_data_dir / 'config.md'
        location_label = QLabel(f"  |  📁 Settings saved to: {config_location}")
        location_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(location_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Configuration form - more compact
        form_widget = QGroupBox("Credentials")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(10)
        
        # Tenant ID row
        tenant_layout = QHBoxLayout()
        tenant_label = QLabel("Tenant ID:")
        tenant_label.setFixedWidth(180)
        tenant_layout.addWidget(tenant_label)
        self.config_tenant_input = QLineEdit()
        self.config_tenant_input.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        tenant_layout.addWidget(self.config_tenant_input)
        form_layout.addLayout(tenant_layout)
        
        # Client ID row
        client_layout = QHBoxLayout()
        client_label = QLabel("Client ID (Application ID):")
        client_label.setFixedWidth(180)
        client_layout.addWidget(client_label)
        self.config_client_input = QLineEdit()
        self.config_client_input.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        client_layout.addWidget(self.config_client_input)
        form_layout.addLayout(client_layout)
        
        # Client Secret row
        secret_layout = QHBoxLayout()
        secret_label = QLabel("Client Secret:")
        secret_label.setFixedWidth(180)
        secret_layout.addWidget(secret_label)
        self.config_secret_input = QLineEdit()
        self.config_secret_input.setPlaceholderText("Enter your client secret")
        self.config_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        secret_layout.addWidget(self.config_secret_input)
        
        # Toggle show/hide password
        self.config_secret_toggle = QPushButton(qta.icon('fa5s.eye'), "")
        self.config_secret_toggle.setMaximumWidth(40)
        self.config_secret_toggle.setCheckable(True)
        self.config_secret_toggle.clicked.connect(self.toggle_secret_visibility)
        secret_layout.addWidget(self.config_secret_toggle)
        form_layout.addLayout(secret_layout)
        
        layout.addWidget(form_widget)
        
        # Buttons on one line with save on right
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton(qta.icon('fa5s.file-download'), "Load from config.md")
        load_btn.clicked.connect(self.load_config)
        button_layout.addWidget(load_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton(qta.icon('fa5s.save'), "Save to config.md")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        # Status message
        self.config_status = QLabel("")
        self.config_status.setStyleSheet("padding: 10px; font-weight: bold;")
        self.config_status.setWordWrap(True)
        layout.addWidget(self.config_status)
        
        # Logs Management Section
        logs_group = QGroupBox("📋 Logs Management")
        logs_layout = QHBoxLayout(logs_group)
        logs_layout.setContentsMargins(10, 10, 10, 10)
        logs_layout.setSpacing(10)
        
        logs_info = QLabel("Manage application logs and export for troubleshooting:")
        logs_info.setStyleSheet("color: #666; font-size: 11px;")
        logs_layout.addWidget(logs_info)
        
        logs_layout.addStretch()
        
        clear_logs_btn = QPushButton(qta.icon('fa5s.trash'), "Clear Logs")
        clear_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        clear_logs_btn.clicked.connect(self.clear_logs)
        logs_layout.addWidget(clear_logs_btn)
        
        export_logs_btn = QPushButton(qta.icon('fa5s.file-export'), "Export Logs")
        export_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        export_logs_btn.clicked.connect(self.export_logs)
        logs_layout.addWidget(export_logs_btn)
        
        layout.addWidget(logs_group)
        
        # Help section - more compact
        help_group = QGroupBox("How to get these credentials:")
        help_layout = QVBoxLayout(help_group)
        help_layout.setContentsMargins(10, 10, 10, 10)
        
        help_text = QLabel(
            "1. Go to Azure Portal → Azure Active Directory → App registrations<br>"
            "2. Create or select your application<br>"
            "3. Copy the Tenant ID and Client ID from Overview page<br>"
            "4. Go to Certificates & secrets → Create new client secret<br>"
            "5. Copy the secret value immediately (it won't be shown again)"
        )
        help_text.setStyleSheet("color: #666; font-size: 11px;")
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        
        # Setup guide button inside help group (only if file exists)
        if getattr(sys, 'frozen', False):
            # Running as exe
            guide_path = Path(sys.argv[0]).parent / "AZURE_APP_SETUP.md"
        else:
            # Running from source
            guide_path = Path(__file__).parent.parent.parent / "AZURE_APP_SETUP.md"
        
        if guide_path.exists():
            guide_btn = QPushButton(qta.icon('fa5s.book'), "📖 View Complete Azure App Setup Guide")
            guide_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17a2b8;
                    color: white;
                    padding: 8px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
            """)
            guide_btn.clicked.connect(self.open_azure_setup_guide)
            help_layout.addWidget(guide_btn)
        
        layout.addWidget(help_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, qta.icon('fa5s.cog', color=self._get_tab_icon_color()), "Configuration")
        
        # Auto-load config on startup
        QTimer.singleShot(100, self.load_config)
    
    def toggle_secret_visibility(self):
        """Toggle password visibility"""
        if self.config_secret_toggle.isChecked():
            self.config_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.config_secret_toggle.setIcon(qta.icon('fa5s.eye-slash'))
        else:
            self.config_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.config_secret_toggle.setIcon(qta.icon('fa5s.eye'))
    
    def load_config(self):
        """Load configuration from config.md"""
        try:
            # Use AppData for config (writable location, not Program Files)
            config_path = self.app_data_dir / "config.md"
            
            if not config_path.exists():
                self.config_status.setText("⚠️ config.md not found. Please enter credentials and save.")
                self.config_status.setStyleSheet("padding: 10px; color: orange; font-weight: bold;")
                return
            
            # Read config file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Extract values using regex
            import re
            tenant_match = re.search(r'tenantId\s*=\s*"([^"]+)"', config_content)
            client_match = re.search(r'clientId\s*=\s*"([^"]+)"', config_content)
            secret_match = re.search(r'clientSecret\s*=\s*"([^"]+)"', config_content)
            
            if tenant_match:
                self.config_tenant_input.setText(tenant_match.group(1))
            if client_match:
                self.config_client_input.setText(client_match.group(1))
            if secret_match:
                self.config_secret_input.setText(secret_match.group(1))
            
            self.config_status.setText("✓ Configuration loaded successfully!")
            self.config_status.setStyleSheet("padding: 10px; color: green; font-weight: bold;")
            
        except Exception as e:
            self.config_status.setText(f"✗ Error loading config: {str(e)}")
            self.config_status.setStyleSheet("padding: 10px; color: red; font-weight: bold;")
    
    def save_config(self):
        """Save configuration to config.md"""
        try:
            tenant_id = self.config_tenant_input.text().strip()
            client_id = self.config_client_input.text().strip()
            client_secret = self.config_secret_input.text().strip()
            
            # Validate inputs
            if not tenant_id or not client_id or not client_secret:
                QMessageBox.warning(self, "Validation Error", 
                    "All fields are required. Please fill in all credentials.")
                return
            
            # Basic GUID validation for tenant and client IDs
            guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            if not re.match(guid_pattern, tenant_id):
                QMessageBox.warning(self, "Validation Error", 
                    "Tenant ID must be a valid GUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")
                return
            if not re.match(guid_pattern, client_id):
                QMessageBox.warning(self, "Validation Error", 
                    "Client ID must be a valid GUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")
                return
            
            # Use AppData for config (writable location)
            config_path = self.app_data_dir / "config.md"
            
            # Create config content
            config_content = f'''# Fabric Configuration

tenantId = "{tenant_id}"
clientId = "{client_id}"
clientSecret = "{client_secret}"
'''
            
            # Write to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            self.config_status.setText(f"✓ Configuration saved successfully to:\n{config_path}")
            self.config_status.setStyleSheet("padding: 10px; color: green; font-weight: bold;")
            
            QMessageBox.information(self, "Success", 
                f"Configuration saved successfully!\n\nFile: {config_path}\n\n"
                "You can now use the Download and Publish features.")
            
        except Exception as e:
            self.config_status.setText(f"✗ Error saving config: {str(e)}")
            self.config_status.setStyleSheet("padding: 10px; color: red; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")

    # OLD DOWNLOAD TAB - REMOVED (replaced by FabricCLITab which is now called "Download from Fabric")
    # def create_download_tab(self):
    #     """Create Download from Fabric tab"""
    #     ...removed code...
    
    def create_assessment_tab(self):
        """Create Assessment & Indexing tab with management dashboard"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Compact header with info inline
        header_layout = QHBoxLayout()
        
        info_label = QLabel("📊 Assessment: Index & analyze Power BI exports, track workspaces, datasets, tables & data sources")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(info_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Top section: Export folder selection and actions
        folder_group = QGroupBox("📂 Export Folder & Actions")
        folder_layout = QVBoxLayout()
        folder_layout.setSpacing(8)
        folder_layout.setContentsMargins(5, 5, 5, 5)
        
        # Row 1: Dropdown with Scan button aligned to Browse position
        dropdown_layout = QHBoxLayout()
        dropdown_layout.setSpacing(8)
        dropdown_label = QLabel("Available Exports:")
        dropdown_label.setFixedWidth(120)
        dropdown_layout.addWidget(dropdown_label)
        
        # Create a container for dropdown to control its width
        dropdown_container = QHBoxLayout()
        dropdown_container.setSpacing(0)
        self.export_dropdown = QComboBox()
        self.export_dropdown.currentTextChanged.connect(self.on_export_selected)
        dropdown_container.addWidget(self.export_dropdown, 1)
        dropdown_layout.addLayout(dropdown_container, 1)
        
        # Refresh dropdown button
        refresh_dropdown_btn = QPushButton(qta.icon('fa5s.sync-alt'), "Refresh")
        refresh_dropdown_btn.setFixedHeight(32)
        refresh_dropdown_btn.setFixedWidth(120)
        refresh_dropdown_btn.setIconSize(QSize(16, 16))
        refresh_dropdown_btn.setToolTip("Refresh export folders list")
        refresh_dropdown_btn.setStyleSheet("background-color: #5a5a5a; color: white; padding: 1px; font-weight: bold; border: none;")
        refresh_dropdown_btn.clicked.connect(self.refresh_assessment_dropdown)
        dropdown_layout.addWidget(refresh_dropdown_btn)
        
        # Spacer widgets to align with row 2 buttons
        for _ in range(2):  # Space for Index, Clear DB, Export
            spacer_btn = QPushButton()
            spacer_btn.setFixedWidth(130)
            spacer_btn.setVisible(False)
            dropdown_layout.addWidget(spacer_btn)
        
        folder_layout.addLayout(dropdown_layout)
        
        # Row 2: Manual path input with Browse, Index, Clear DB, Refresh buttons
        manual_layout = QHBoxLayout()
        manual_layout.setSpacing(8)
        manual_label = QLabel("Or Manual Path:")
        manual_label.setFixedWidth(120)
        manual_layout.addWidget(manual_label)
        self.export_path_input = QLineEdit()
        self.export_path_input.setPlaceholderText("Or enter custom path...")
        manual_layout.addWidget(self.export_path_input, 1)
        
        browse_btn = QPushButton(qta.icon('fa5s.folder-open'), "Browse")
        browse_btn.clicked.connect(self.browse_export_folder)
        browse_btn.setFixedHeight(32)
        browse_btn.setFixedWidth(100)
        browse_btn.setStyleSheet("background-color: #5a5a5a; color: white; padding: 1px; font-weight: bold; border: none;")
        browse_btn.setIconSize(QSize(16, 16))
        manual_layout.addWidget(browse_btn)
        
        # Index button
        index_btn = QPushButton(qta.icon('fa5s.database'), "Index")
        index_btn.setFixedHeight(32)
        index_btn.setFixedWidth(130)
        index_btn.setIconSize(QSize(16, 16))
        index_btn.setToolTip("Index selected export (appends to existing data)")
        index_btn.setStyleSheet("background: #27ae60; color: white; padding: 5px 10px; font-weight: bold;")
        index_btn.clicked.connect(self.index_export)
        manual_layout.addWidget(index_btn)
        
        # Clear Database button
        clear_btn = QPushButton(qta.icon('fa5s.trash-alt'), "Clear DB")
        clear_btn.setFixedHeight(32)
        clear_btn.setFixedWidth(130)
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.setToolTip("Delete all indexed data from database")
        clear_btn.setStyleSheet("background: #e74c3c; color: white; padding: 5px 10px; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_database)
        manual_layout.addWidget(clear_btn)
        
        # Export Data button
        export_btn = QPushButton(qta.icon('fa5s.file-export'), "Export")
        export_btn.setFixedHeight(32)
        export_btn.setFixedWidth(130)
        export_btn.setIconSize(QSize(16, 16))
        export_btn.setToolTip("Export database tables to Excel")
        export_btn.setStyleSheet("background: #9b59b6; color: white; padding: 5px 10px; font-weight: bold;")
        export_btn.clicked.connect(self.export_database_to_excel)
        manual_layout.addWidget(export_btn)
        
        folder_layout.addLayout(manual_layout)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Filter Section with counts integrated in labels
        filter_group = QGroupBox("🔍 Filters")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(5, 5, 5, 5)
        
        # Workspace filter
        workspace_container = QVBoxLayout()
        workspace_container.setSpacing(2)
        self.workspace_label = QLabel("Workspace (0)")
        self.workspace_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        workspace_container.addWidget(self.workspace_label)
        self.filter_workspace = QComboBox()
        self.filter_workspace.addItem("All Workspaces")
        self.filter_workspace.currentTextChanged.connect(self.apply_filters)
        workspace_container.addWidget(self.filter_workspace)
        filter_layout.addLayout(workspace_container, 1)
        
        # Dataset filter
        dataset_container = QVBoxLayout()
        dataset_container.setSpacing(2)
        self.dataset_label = QLabel("Dataset (0)")
        self.dataset_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        dataset_container.addWidget(self.dataset_label)
        self.filter_dataset = QComboBox()
        self.filter_dataset.addItem("All Datasets")
        self.filter_dataset.currentTextChanged.connect(self.apply_filters)
        dataset_container.addWidget(self.filter_dataset)
        filter_layout.addLayout(dataset_container, 1)
        
        # Source Type filter
        source_container = QVBoxLayout()
        source_container.setSpacing(2)
        self.source_label = QLabel("Source Type")
        self.source_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        source_container.addWidget(self.source_label)
        self.filter_source = QComboBox()
        self.filter_source.addItem("All Sources")
        self.filter_source.currentTextChanged.connect(self.apply_filters)
        source_container.addWidget(self.filter_source)
        filter_layout.addLayout(source_container, 1)
        
        # Table name filter
        table_container = QVBoxLayout()
        table_container.setSpacing(2)
        table_label = QLabel("Table Search")
        table_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        table_container.addWidget(table_label)
        self.filter_table = QLineEdit()
        self.filter_table.setPlaceholderText("Search table...")
        self.filter_table.textChanged.connect(self.apply_filters)
        table_container.addWidget(self.filter_table)
        filter_layout.addLayout(table_container, 1)
        
        # Relationship Type filter
        relationships_container = QVBoxLayout()
        relationships_container.setSpacing(2)
        relationships_label = QLabel("Relationship Type")
        relationships_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        relationships_container.addWidget(relationships_label)
        self.filter_relationships = QComboBox()
        self.filter_relationships.addItems(["All", "one-to-many", "many-to-one", "one-to-one", "many-to-many"])
        self.filter_relationships.currentTextChanged.connect(self.apply_filters)
        relationships_container.addWidget(self.filter_relationships)
        filter_layout.addLayout(relationships_container, 1)
        
        # Clear filters button - aligned at bottom like dropdowns
        clear_container = QVBoxLayout()
        clear_container.setSpacing(2)
        clear_spacer = QLabel("")  # Empty label for spacing to match dropdown labels
        clear_spacer.setStyleSheet("font-size: 11px;")
        clear_container.addWidget(clear_spacer)
        self.clear_filters_btn = QPushButton(qta.icon('fa5s.times-circle'), "Clear")
        self.clear_filters_btn.setFixedHeight(26)  # Match dropdown height
        self.clear_filters_btn.setStyleSheet("background: #bdc3c7; color: white; padding: 3px 8px; font-weight: bold;")
        self.clear_filters_btn.setEnabled(False)
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        clear_container.addWidget(self.clear_filters_btn)
        filter_layout.addLayout(clear_container, 0)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Horizontal layout for side-by-side panels
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(10)
        
        # LEFT SIDE: Main Details Table (as Tree for grouping)
        details_group = QGroupBox("📊 Detailed Assessment View")
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(5, 5, 5, 5)
        details_layout.setSpacing(5)
        
        self.details_table = QTreeWidget()
        self.details_table.setColumnCount(5)
        self.details_table.setHeaderLabels([
            "Workspace / Dataset / Table",
            "Hidden",
            "Columns",
            "Source Types",
            "Partitions"
        ])
        self.details_table.setUniformRowHeights(True)
        self.details_table.setStyleSheet("QTreeWidget::item { height: 20px; }")
        self.details_table.header().setStretchLastSection(True)
        self.details_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.details_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.details_table.setSortingEnabled(False)  # Disable for hierarchical structure
        self.details_table.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.details_table.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.details_table.itemSelectionChanged.connect(self.on_table_row_selected)
        # Add double-click to unselect and show all details
        self.details_table.itemDoubleClicked.connect(self.unselect_and_show_all)
        self.details_table.setAlternatingRowColors(True)
        self.details_table.setIndentation(20)
        details_layout.addWidget(self.details_table)
        details_group.setLayout(details_layout)
        panels_layout.addWidget(details_group, 1)  # stretch factor 1
        
        # RIGHT SIDE: Detail panel with tabs (initially hidden)
        self.detail_panel = QGroupBox("📋 Table Details")
        self.detail_panel.setVisible(False)
        detail_panel_layout = QVBoxLayout()
        detail_panel_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with Selected Table label and Close button on same line
        header_layout = QHBoxLayout()
        self.selected_table_label = QLabel("All Tables")
        self.selected_table_label.setStyleSheet("font-weight: bold; color: #3498db;")
        header_layout.addWidget(self.selected_table_label)
        header_layout.addStretch()
        close_detail_btn = QPushButton(qta.icon('fa5s.times'), "Close")
        close_detail_btn.clicked.connect(lambda: self.detail_panel.setVisible(False))
        header_layout.addWidget(close_detail_btn)
        detail_panel_layout.addLayout(header_layout)
        
        # Tab widget for different detail views
        self.detail_tabs = QTabWidget()
        
        # Relationships tab
        self.relationships_table = QTableWidget()
        self.relationships_table.setColumnCount(8)
        self.relationships_table.setHorizontalHeaderLabels([
            "Workspace", "Dataset", "From Table", "From Column", "To Table", "To Column", "Cardinality", "Active"
        ])
        self.relationships_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.relationships_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.detail_tabs.addTab(self.relationships_table, "🔗 Relationships")
        
        # Measures tab
        self.measures_table = QTableWidget()
        self.measures_table.setColumnCount(6)
        self.measures_table.setHorizontalHeaderLabels([
            "Workspace", "Dataset", "Measure Name", "Expression", "Format", "Hidden"
        ])
        self.measures_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.measures_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.detail_tabs.addTab(self.measures_table, "📊 Measures")
        
        # Columns tab
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(8)
        self.columns_table.setHorizontalHeaderLabels([
            "Workspace", "Dataset", "Table Name", "Column Name", "Data Type", "Format", "Source", "Hidden"
        ])
        self.columns_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.columns_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.detail_tabs.addTab(self.columns_table, "📋 Columns")
        
        # Power Query tab
        self.powerquery_text = QPlainTextEdit()
        self.powerquery_text.setReadOnly(True)
        self.powerquery_text.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 10pt;")
        self.detail_tabs.addTab(self.powerquery_text, "⚡ Power Query (M)")
        
        detail_panel_layout.addWidget(self.detail_tabs)
        self.detail_panel.setLayout(detail_panel_layout)
        panels_layout.addWidget(self.detail_panel, 1)  # stretch factor 1
        
        layout.addLayout(panels_layout)
        
        self.tabs.addTab(tab, qta.icon('fa5s.file-import', color=self._get_tab_icon_color()), "Assessment")
        
    def create_migration_tab(self):
        """Create Data Source Migration tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Compact header with info inline
        header_layout = QHBoxLayout()
        
        info_label = QLabel("🔄 Bulk Migrate: Select multiple models, filter by source type, migrate to single target")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(info_label)
        
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Main horizontal split: Left (Models) | Right (Filters + Target + Execute)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # ============ LEFT SIDE: Model Selection ============
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        model_group = QGroupBox("1️⃣ Select Semantic Models")
        model_layout = QVBoxLayout()
        model_layout.setSpacing(0)
        model_layout.setContentsMargins(5, 5, 5, 5)
        
        # Scan button and select all
        top_buttons = QHBoxLayout()
        top_buttons.setSpacing(5)
        scan_models_btn = QPushButton(qta.icon('fa5s.sync'), "Scan Models")
        scan_models_btn.clicked.connect(self.scan_migration_models)
        top_buttons.addWidget(scan_models_btn)
        
        select_all_btn = QPushButton(qta.icon('fa5s.check-square'), "Select All")
        select_all_btn.clicked.connect(self.select_all_models)
        top_buttons.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton(qta.icon('fa5s.square'), "Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_models)
        top_buttons.addWidget(deselect_all_btn)
        top_buttons.addStretch()
        model_layout.addLayout(top_buttons)
        
        # Models table with scrollbars
        self.migration_models_table = QTableWidget()
        self.migration_models_table.setColumnCount(4)
        self.migration_models_table.setHorizontalHeaderLabels(["Select", "Workspace", "Model Name", "Sources"])
        self.migration_models_table.horizontalHeader().setStretchLastSection(False)
        self.migration_models_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.migration_models_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.migration_models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.migration_models_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.migration_models_table.setColumnWidth(1, 150)
        self.migration_models_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.migration_models_table.setMinimumHeight(200)
        self.migration_models_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.migration_models_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.migration_models_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        model_layout.addWidget(self.migration_models_table)
        
        model_group.setLayout(model_layout)
        left_layout.addWidget(model_group)
        
        content_layout.addWidget(left_container, 1)  # 50% width (1:1 ratio)
        
        # ============ RIGHT SIDE: Filters + Target + Execute ============
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Source filter strategy
        source_group = QGroupBox("⚙️ Source Filter")
        source_layout = QVBoxLayout()
        source_layout.setSpacing(5)
        source_layout.setContentsMargins(5, 5, 5, 5)
        
        # Dynamic filter container - will be populated after scan
        self.migration_filter_container = QWidget()
        self.migration_filter_layout = QVBoxLayout(self.migration_filter_container)
        self.migration_filter_layout.setContentsMargins(0, 0, 0, 0)
        self.migration_filter_layout.setSpacing(8)
        
        # Default message before scan
        self.migration_filter_placeholder = QLabel("📋 Scan models to see available source types")
        self.migration_filter_placeholder.setStyleSheet("padding: 10px; border-radius: 3px; color: #7f8c8d; font-style: italic; font-size: 11px;")
        self.migration_filter_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.migration_filter_layout.addWidget(self.migration_filter_placeholder)
        
        source_layout.addWidget(self.migration_filter_container)
        
        self.migration_filter_info = QLabel("")
        self.migration_filter_info.setStyleSheet("padding: 8px; border-radius: 3px; color: #2c3e50; font-weight: bold; font-size: 11px;")
        self.migration_filter_info.setWordWrap(True)
        self.migration_filter_info.setVisible(False)
        source_layout.addWidget(self.migration_filter_info)
        
        source_group.setLayout(source_layout)
        right_layout.addWidget(source_group)
        
        right_layout.addStretch()
        
        # Target configuration (single target for all) - at bottom
        target_group = QGroupBox("🎯 Target Configuration")
        target_layout = QVBoxLayout()
        target_layout.setSpacing(5)
        target_layout.setContentsMargins(5, 5, 5, 5)
        
        target_type_layout = QHBoxLayout()
        target_type_layout.addWidget(QLabel("Target Type:"))
        self.migration_target_combo = QComboBox()
        # Populate dropdown with display names
        self.migration_target_keys = ["SQL_Server", "Snowflake", "Lakehouse", "Excel"]
        for key in self.migration_target_keys:
            display_name = DATA_SOURCE_TEMPLATES.get(key, {}).get('display_name', key)
            self.migration_target_combo.addItem(display_name, key)
        self.migration_target_combo.currentIndexChanged.connect(self.on_target_type_changed)
        target_type_layout.addWidget(self.migration_target_combo, 1)
        target_layout.addLayout(target_type_layout)
        
        self.migration_target_inputs = QWidget()
        self.migration_target_inputs_layout = QGridLayout()
        self.migration_target_inputs_layout.setSpacing(8)
        self.migration_target_inputs_layout.setContentsMargins(5, 5, 5, 5)
        self.migration_target_inputs.setLayout(self.migration_target_inputs_layout)
        target_layout.addWidget(self.migration_target_inputs)
        
        target_group.setLayout(target_layout)
        right_layout.addWidget(target_group)
        
        content_layout.addWidget(right_container, 1)  # 50% width (1:1 ratio)
        
        main_layout.addLayout(content_layout)
        
        # Execute button above progress bar and logs
        execute_layout = QHBoxLayout()
        execute_layout.addStretch()
        
        # Execute with preview button (left)
        migrate_btn = QPushButton(qta.icon('fa5s.search-plus'), " Preview & Execute Migration")
        migrate_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background: #229954;
            }
            QPushButton:pressed {
                background: #1e8449;
            }
        """)
        migrate_btn.clicked.connect(self.execute_bulk_migration)
        execute_layout.addWidget(migrate_btn)
        
        # Execute without preview button (right)
        migrate_no_preview_btn = QPushButton(qta.icon('fa5s.bolt'), " Execute Without Preview")
        migrate_no_preview_btn.setStyleSheet("""
            QPushButton {
                background: #f39c12;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background: #e67e22;
            }
            QPushButton:pressed {
                background: #d35400;
            }
        """)
        migrate_no_preview_btn.clicked.connect(self.execute_bulk_migration_no_preview)
        execute_layout.addWidget(migrate_no_preview_btn)
        
        main_layout.addLayout(execute_layout)
        
        # Progress bar for bulk migration
        self.migration_progress = QProgressBar()
        self.migration_progress.setVisible(False)
        self.migration_progress.setStyleSheet("QProgressBar { height: 25px; text-align: center; font-weight: bold; }")
        main_layout.addWidget(self.migration_progress)
        
        # Results - reduced height
        self.migration_results = QTextEdit()
        self.migration_results.setReadOnly(True)
        self.migration_results.setMinimumHeight(120)
        self.migration_results.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background: #34495e; color: #ecf0f1; padding: 8px;")
        main_layout.addWidget(self.migration_results)
        
        self.tabs.addTab(tab, qta.icon('fa5s.exchange-alt', color=self._get_tab_icon_color()), "Data Source Migration")
        
        # Initialize
        self.migration_sources = []
        self.current_source_info = None
        self.on_target_type_changed(0)  # Initialize with first item
    
    def create_preview_tab(self):
        """Create Migration Preview tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with info
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 8, 15, 8)
        header_layout.setSpacing(20)
        
        # Preview info labels
        self.preview_files_label = QLabel("📁 <b>0</b> Files")
        self.preview_files_label.setStyleSheet("color: #3498db; font-size: 12px;")
        header_layout.addWidget(self.preview_files_label)
        
        self.preview_tables_label = QLabel("📊 <b>0</b> Tables")
        self.preview_tables_label.setStyleSheet("color: #9b59b6; font-size: 12px;")
        header_layout.addWidget(self.preview_tables_label)
        
        self.preview_lines_label = QLabel("📝 <b>0</b> Lines Changed")
        self.preview_lines_label.setStyleSheet("color: #e67e22; font-size: 12px;")
        header_layout.addWidget(self.preview_lines_label)
        
        header_layout.addStretch()
        
        self.preview_connection_label = QLabel("")
        self.preview_connection_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        header_layout.addWidget(self.preview_connection_label)
        
        main_layout.addWidget(header_widget)
        
        # File list and diff viewer
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File tree
        file_container = QWidget()
        file_layout = QVBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(0)
        
        file_header = QLabel("  📁 Files to Change")
        file_header.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                border-bottom: 1px solid #3a3a3a;
            }
        """)
        file_layout.addWidget(file_header)
        
        self.preview_file_tree = QTreeWidget()
        self.preview_file_tree.setHeaderLabels(["File", "Changes"])
        self.preview_file_tree.setColumnWidth(0, 220)
        self.preview_file_tree.itemSelectionChanged.connect(self.on_preview_file_selected)
        file_layout.addWidget(self.preview_file_tree)
        
        # Right: Diff viewer container
        diff_container = QWidget()
        diff_layout = QVBoxLayout(diff_container)
        diff_layout.setContentsMargins(0, 0, 0, 0)
        diff_layout.setSpacing(0)
        
        # Side-by-side diff viewer
        self.preview_diff_viewer = SideBySideDiffViewer()
        diff_layout.addWidget(self.preview_diff_viewer)
        
        splitter.addWidget(file_container)
        splitter.addWidget(diff_container)
        splitter.setStretchFactor(0, 30)
        splitter.setStretchFactor(1, 70)
        
        main_layout.addWidget(splitter, 1)
        
        # Bottom action buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(20, 12, 20, 12)
        button_layout.setSpacing(10)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton(qta.icon('fa5s.times', color='black'), " Back to Migration")
        cancel_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))  # Go back to Migration tab
        button_layout.addWidget(cancel_btn)
        
        # Apply button
        apply_btn = QPushButton(qta.icon('fa5s.check', color='black'), " Apply Changes")
        apply_btn.clicked.connect(self.apply_preview_changes)
        button_layout.addWidget(apply_btn)
        
        main_layout.addWidget(button_widget)
        
        # Store preview data
        self.preview_data = None
        
        self.tabs.addTab(tab, qta.icon('fa5s.search-plus', color=self._get_tab_icon_color()), "Migration Preview")
        
    def on_preview_file_selected(self):
        """Handle file selection in preview tab"""
        selected_items = self.preview_file_tree.selectedItems()
        if not selected_items or not self.preview_data:
            return
        
        file_change = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        self.preview_show_diff(file_change)
    
    def preview_show_diff(self, file_change: dict):
        """Display diff for selected file in preview tab"""
        old_content = file_change.get('old_content', '')
        new_content = file_change.get('new_content', '')
        
        if old_content == new_content:
            self.preview_diff_viewer.set_diff("No changes", "No changes")
            return
        
        self.preview_diff_viewer.set_diff(old_content, new_content)
    
    def preview_show_previous_file(self):
        """Navigate to previous file in preview"""
        current = self.preview_file_tree.currentItem()
        if current:
            index = self.preview_file_tree.indexOfTopLevelItem(current)
            if index > 0:
                self.preview_file_tree.setCurrentItem(self.preview_file_tree.topLevelItem(index - 1))
    
    def preview_show_next_file(self):
        """Navigate to next file in preview"""
        current = self.preview_file_tree.currentItem()
        if current:
            index = self.preview_file_tree.indexOfTopLevelItem(current)
            if index < self.preview_file_tree.topLevelItemCount() - 1:
                self.preview_file_tree.setCurrentItem(self.preview_file_tree.topLevelItem(index + 1))
    
    def load_preview_data(self, preview_data: dict):
        """Load preview data into the preview tab"""
        self.preview_data = preview_data
        
        # Update header
        summary = preview_data['summary']
        num_models = len(preview_data.get('models_preview', []))
        model_info = f" across {num_models} model(s)" if num_models > 1 else ""
        self.preview_files_label.setText(f"📁 <b>{summary['total_files']}</b> Files{model_info}")
        self.preview_tables_label.setText(f"📊 <b>{summary['total_tables']}</b> Tables")
        self.preview_lines_label.setText(f"📝 <b>{summary['total_lines_changed']}</b> Lines Changed")
        
        # Connection info
        conn_parts = []
        for param, value in summary['connection_changes'].items():
            conn_parts.append(f"{param}={value}")
        self.preview_connection_label.setText(" | ".join(conn_parts))
        
        # Populate file tree - organize by model if multiple models
        self.preview_file_tree.clear()
        
        if len(preview_data.get('models_preview', [])) > 1:
            # Multiple models - organize hierarchically by semantic model (like VS Code)
            for model_preview in preview_data['models_preview']:
                # Extract just the folder name from model path for cleaner display
                model_folder_name = Path(model_preview['model_path']).name if model_preview['model_path'] != 'Multiple Models' else model_preview['model_name']
                
                # Create model parent node (collapsed by default for cleaner view)
                model_item = QTreeWidgetItem(self.preview_file_tree)
                model_item.setText(0, f"📁 {model_folder_name}")
                model_item.setText(1, f"{model_preview['summary']['total_tables']} tables")
                model_item.setForeground(0, QColor("#3498db"))
                model_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
                
                # Add table files under model (no extra indent, just like VS Code)
                for file_change in model_preview['files_to_change']:
                    file_item = QTreeWidgetItem(model_item)
                    file_item.setText(0, f"📄 {file_change['table_name']}")
                    file_item.setText(1, f"+{file_change['lines_added']} -{file_change['lines_removed']}")
                    file_item.setData(0, Qt.ItemDataRole.UserRole, file_change)
                    
                    # Color code by change magnitude
                    if file_change['lines_changed'] > 10:
                        file_item.setForeground(1, QColor("#f48771"))
                    elif file_change['lines_changed'] > 5:
                        file_item.setForeground(1, QColor("#dcdcaa"))
                    else:
                        file_item.setForeground(1, QColor("#4ec9b0"))
                
                model_item.setExpanded(True)  # Expand by default to see all tables
        else:
            # Single model - show with model name as parent
            model_folder_name = Path(preview_data['model_path']).name if preview_data['model_path'] != 'Multiple Models' else preview_data['model_name']
            
            model_item = QTreeWidgetItem(self.preview_file_tree)
            model_item.setText(0, f"📁 {model_folder_name}")
            model_item.setText(1, f"{len(preview_data['files_to_change'])} tables")
            model_item.setForeground(0, QColor("#3498db"))
            model_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            
            for file_change in preview_data['files_to_change']:
                file_item = QTreeWidgetItem(model_item)
                file_item.setText(0, f"📄 {file_change['table_name']}")
                file_item.setText(1, f"+{file_change['lines_added']} -{file_change['lines_removed']}")
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_change)
                
                # Color code by change magnitude
                if file_change['lines_changed'] > 10:
                    file_item.setForeground(1, QColor("#f48771"))
                elif file_change['lines_changed'] > 5:
                    file_item.setForeground(1, QColor("#dcdcaa"))
                else:
                    file_item.setForeground(1, QColor("#4ec9b0"))
            
            model_item.setExpanded(True)
        
        # Select first file (skip model nodes if hierarchical)
        if self.preview_file_tree.topLevelItemCount() > 0:
            first_item = self.preview_file_tree.topLevelItem(0)
            if first_item.childCount() > 0:
                # Has children (model node), select first child
                self.preview_file_tree.setCurrentItem(first_item.child(0))
            else:
                # No children (flat list)
                self.preview_file_tree.setCurrentItem(first_item)
        
        # Switch to preview tab
        self.tabs.setCurrentIndex(4)  # Preview tab index
    
    def apply_preview_changes(self):
        """Apply the migration changes after preview confirmation"""
        if not self.preview_data:
            QMessageBox.warning(self, "No Preview", "No preview data available.")
            return
        
        # Build confirmation message with model breakdown
        num_models = len(self.preview_data.get('models_preview', []))
        if num_models > 1:
            model_breakdown = "\n".join([
                f"  • {mp['model_name']}: {mp['summary']['total_tables']} tables"
                for mp in self.preview_data.get('models_preview', [])
            ])
            confirmation_msg = (
                f"Apply migration changes to {num_models} semantic models?\n\n"
                f"{model_breakdown}\n\n"
                f"Total: {self.preview_data['summary']['total_files']} files, "
                f"{self.preview_data['summary']['total_lines_changed']} lines changed.\n\n"
                f"Each model will be processed separately to prevent table mixing."
            )
        else:
            confirmation_msg = (
                f"Apply migration changes to {self.preview_data['summary']['total_files']} files?\n\n"
                f"This will modify {self.preview_data['summary']['total_tables']} tables with "
                f"{self.preview_data['summary']['total_lines_changed']} lines changed."
            )
        
        reply = QMessageBox.question(
            self,
            "Confirm Migration",
            confirmation_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Execute the actual migration
            self.execute_migration_from_preview()
        
    def create_restore_tab(self):
        """Create Restore from Backup tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        info_label = QLabel("♻️ Restore from Backup: Browse and restore semantic models/reports from previous migrations")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Main horizontal split: Backups List (50%) | Restore Details (50%)
        content_layout = QHBoxLayout()
        
        # ============ LEFT: Backups List ============
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scan backups button
        scan_backup_btn = QPushButton(qta.icon('fa5s.search'), "Scan for Backups")
        scan_backup_btn.clicked.connect(self.scan_backups)
        left_layout.addWidget(scan_backup_btn)
        
        # Backups table
        backups_group = QGroupBox("Available Backups")
        backups_layout = QVBoxLayout()
        
        self.restore_backups_table = QTableWidget()
        self.restore_backups_table.setColumnCount(5)
        self.restore_backups_table.setHorizontalHeaderLabels([
            "Workspace", "Model", "Backup Time", "Contents", "Size (MB)"
        ])
        self.restore_backups_table.horizontalHeader().setStretchLastSection(False)
        # Make all columns interactive (manually resizable)
        self.restore_backups_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.restore_backups_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        # Set initial widths
        self.restore_backups_table.setColumnWidth(0, 200)  # Workspace
        self.restore_backups_table.setColumnWidth(1, 250)  # Model
        self.restore_backups_table.setColumnWidth(2, 180)  # Backup Time
        self.restore_backups_table.setColumnWidth(3, 150)  # Contents
        self.restore_backups_table.setColumnWidth(4, 100)  # Size
        self.restore_backups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.restore_backups_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.restore_backups_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.restore_backups_table.itemSelectionChanged.connect(self.on_backup_selected)
        
        backups_layout.addWidget(self.restore_backups_table)
        backups_group.setLayout(backups_layout)
        left_layout.addWidget(backups_group)
        
        content_layout.addWidget(left_container, 50)
        
        # ============ RIGHT: Backup Details ============
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Backup Details
        details_group = QGroupBox("Backup Details")
        details_layout = QVBoxLayout()
        
        self.restore_details_text = QTextEdit()
        self.restore_details_text.setReadOnly(True)
        self.restore_details_text.setMaximumHeight(150)
        self.restore_details_text.setPlaceholderText("Select a backup to view details...")
        details_layout.addWidget(self.restore_details_text)
        
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        # Restore button
        self.restore_execute_btn = QPushButton(qta.icon('fa5s.undo'), "Restore Selected Backup")
        self.restore_execute_btn.setEnabled(False)
        self.restore_execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                font-weight: bold;
                padding: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.restore_execute_btn.clicked.connect(self.execute_restore)
        right_layout.addWidget(self.restore_execute_btn)
        
        # Results
        results_group = QGroupBox("Restore Results")
        results_layout = QVBoxLayout()
        
        self.restore_results_text = QTextEdit()
        self.restore_results_text.setReadOnly(True)
        self.restore_results_text.setPlaceholderText("Restore results will appear here...")
        results_layout.addWidget(self.restore_results_text)
        
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)
        
        content_layout.addWidget(right_container, 50)
        
        main_layout.addLayout(content_layout)
        
        # Add tab
        self.tabs.addTab(tab, qta.icon('fa5s.history', color=self._get_tab_icon_color()), "Restore")
        
        # Store backup data
        self.restore_backups_data = []
    
    def scan_backups(self):
        """Scan BACKUP folder and populate table"""
        export_path = self.export_path_input.text() or self.export_dropdown.currentText()
        if not export_path or not Path(export_path).exists():
            QMessageBox.warning(self, "Warning", "Please index an export first in Assessment tab")
            return
        
        # Scan for backups
        self.restore_backups_data = scan_backups(export_path)
        
        if not self.restore_backups_data:
            QMessageBox.information(self, "Info", 
                "No backups found.\n\n"
                "Backups are created automatically during data source migration.")
            return
        
        # Populate table
        self.restore_backups_table.setRowCount(len(self.restore_backups_data))
        
        for row, backup in enumerate(self.restore_backups_data):
            # Workspace
            self.restore_backups_table.setItem(row, 0, QTableWidgetItem(backup['workspace']))
            
            # Model Name
            self.restore_backups_table.setItem(row, 1, QTableWidgetItem(backup['model_name']))
            
            # Timestamp
            self.restore_backups_table.setItem(row, 2, QTableWidgetItem(backup['timestamp']))
            
            # Contents
            contents = []
            if backup['has_semantic_model']:
                contents.append("📊 Model")
            if backup['has_report']:
                contents.append("📄 Report")
            contents_str = " + ".join(contents) if contents else "Empty"
            self.restore_backups_table.setItem(row, 3, QTableWidgetItem(contents_str))
            
            # Size
            self.restore_backups_table.setItem(row, 4, QTableWidgetItem(str(backup['size_mb'])))
        
        self.statusBar().showMessage(f"Found {len(self.restore_backups_data)} backup(s)")
    
    def on_backup_selected(self):
        """Handle backup selection"""
        selected_rows = self.restore_backups_table.selectionModel().selectedRows()
        
        if not selected_rows:
            self.restore_execute_btn.setEnabled(False)
            self.restore_details_text.clear()
            return
        
        row = selected_rows[0].row()
        backup = self.restore_backups_data[row]
        
        # Enable restore button
        self.restore_execute_btn.setEnabled(True)
        
        # Show details
        details = f"<b>Backup Information</b><br><br>"
        details += f"<b>Workspace:</b> {backup['workspace']}<br>"
        details += f"<b>Model:</b> {backup['model_name']}<br>"
        details += f"<b>Backup Time:</b> {backup['timestamp']}<br>"
        details += f"<b>Backup Path:</b> {backup['backup_path']}<br><br>"
        
        details += f"<b>Contents:</b><br>"
        if backup['has_semantic_model']:
            details += "  ✓ Semantic Model (.SemanticModel)<br>"
        else:
            details += "  ✗ No Semantic Model<br>"
        
        if backup['has_report']:
            details += "  ✓ Report (.Report)<br>"
        else:
            details += "  ✗ No Report<br>"
        
        details += f"<br><b>Size:</b> {backup['size_mb']} MB<br>"
        
        self.restore_details_text.setHtml(details)
    
    def execute_restore(self):
        """Execute restore operation"""
        # Get selected backup
        selected_rows = self.restore_backups_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a backup to restore")
            return
        
        row = selected_rows[0].row()
        backup = self.restore_backups_data[row]
        
        # Restore everything available in the backup
        restore_semantic = backup['has_semantic_model']
        restore_report = backup['has_report']
        
        if not restore_semantic and not restore_report:
            QMessageBox.warning(self, "Warning", "This backup is empty - nothing to restore")
            return
        
        # Confirm restore
        items = []
        if restore_semantic:
            items.append("Semantic Model")
        if restore_report:
            items.append("Report")
        
        msg = f"Restore from backup:\n\n"
        msg += f"Workspace: {backup['workspace']}\n"
        msg += f"Model: {backup['model_name']}\n"
        msg += f"Backup Time: {backup['timestamp']}\n\n"
        msg += f"Items to restore: {', '.join(items)}\n\n"
        msg += "⚠️ WARNING: This will OVERWRITE the current version!\n"
        msg += "The current files will be replaced with the backup.\n\n"
        msg += "Continue?"
        
        reply = QMessageBox.question(self, "Confirm Restore", msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Find target path
        export_path = self.export_path_input.text() or self.export_dropdown.currentText()
        export_path = Path(export_path)
        
        # Target path: Raw Files/WorkspaceName/
        if (export_path / "Raw Files").exists():
            target_path = export_path / "Raw Files" / backup['workspace']
        elif (export_path / "Processed_Data").exists():
            target_path = export_path / "Processed_Data" / backup['workspace']
        else:
            target_path = export_path / backup['workspace']
        
        if not target_path.exists():
            QMessageBox.critical(self, "Error", 
                f"Target workspace folder not found:\n{target_path}\n\n"
                "Cannot restore backup.")
            return
        
        # Execute restore
        self.restore_results_text.clear()
        self.restore_results_text.append("=" * 60)
        self.restore_results_text.append("RESTORE OPERATION STARTED")
        self.restore_results_text.append("=" * 60)
        self.restore_results_text.append(f"\nBackup: {backup['model_name']}")
        self.restore_results_text.append(f"Time: {backup['timestamp']}")
        self.restore_results_text.append(f"Target: {target_path}\n")
        
        try:
            success_count, error_count, errors = restore_from_backup(
                backup_path=backup['backup_path'],
                target_path=str(target_path),
                restore_semantic_model=restore_semantic,
                restore_report=restore_report
            )
            
            if error_count == 0:
                self.restore_results_text.append("✓ Restore completed successfully!")
                self.restore_results_text.append(f"\nRestored {success_count} item(s)")
                
                QMessageBox.information(self, "Success",
                    f"Restore completed successfully!\n\n"
                    f"✓ Restored {success_count} item(s)\n\n"
                    f"Target: {target_path}")
            else:
                self.restore_results_text.append(f"⚠️ Restore completed with errors")
                self.restore_results_text.append(f"\n✓ Success: {success_count}")
                self.restore_results_text.append(f"✗ Errors: {error_count}\n")
                
                for error in errors:
                    self.restore_results_text.append(f"  • {error}")
                
                QMessageBox.warning(self, "Completed with Errors",
                    f"Restore completed with some errors:\n\n"
                    f"✓ Success: {success_count}\n"
                    f"✗ Errors: {error_count}\n\n"
                    f"Check results panel for details.")
        
        except Exception as e:
            self.restore_results_text.append(f"\n✗ Restore failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Restore failed:\n{str(e)}")
        
        self.restore_results_text.append("\n" + "=" * 60)
        self.restore_results_text.append("RESTORE OPERATION COMPLETED")
        self.restore_results_text.append("=" * 60)
        
    def create_rename_tab(self):
        """Create Table Rename tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Compact header with info inline
        header_layout = QHBoxLayout()
        
        info_label = QLabel("🏷️ Bulk Rename: Select multiple models, apply prefix/suffix, rename all tables and update references")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(info_label)
        
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Main horizontal split: Left (Models + Config - 30%) | Right (Table Preview - 70%)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # ============ LEFT SIDE: Model Selection + Bulk Config (30%) ============
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Model Selection Group
        model_group = QGroupBox("1️⃣ Select Semantic Models")
        model_layout = QVBoxLayout()
        model_layout.setSpacing(0)
        model_layout.setContentsMargins(5, 5, 5, 5)
        
        # Scan button and select all
        top_buttons = QHBoxLayout()
        top_buttons.setSpacing(5)
        scan_rename_btn = QPushButton(qta.icon('fa5s.sync'), "Scan Models")
        scan_rename_btn.clicked.connect(self.scan_rename_models)
        top_buttons.addWidget(scan_rename_btn)
        
        select_all_rename_btn = QPushButton(qta.icon('fa5s.check-square'), "Select All")
        select_all_rename_btn.clicked.connect(self.select_all_rename_models)
        top_buttons.addWidget(select_all_rename_btn)
        
        deselect_all_rename_btn = QPushButton(qta.icon('fa5s.square'), "Deselect All")
        deselect_all_rename_btn.clicked.connect(self.deselect_all_rename_models)
        top_buttons.addWidget(deselect_all_rename_btn)
        model_layout.addLayout(top_buttons)
        
        # Models table with scrollbars
        self.rename_models_table = QTableWidget()
        self.rename_models_table.setColumnCount(4)
        self.rename_models_table.setHorizontalHeaderLabels(["✓", "Workspace", "Model", "Tables"])
        self.rename_models_table.horizontalHeader().setStretchLastSection(False)
        self.rename_models_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.rename_models_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.rename_models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.rename_models_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.rename_models_table.setColumnWidth(1, 120)
        self.rename_models_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.rename_models_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rename_models_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.rename_models_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        model_layout.addWidget(self.rename_models_table)
        
        model_group.setLayout(model_layout)
        left_layout.addWidget(model_group)
        
        left_layout.addStretch()
        
        # Bulk Configuration Group (2 columns for better space usage) - at bottom
        config_group = QGroupBox("2️⃣ Bulk Configuration")
        config_layout = QVBoxLayout()
        config_layout.setSpacing(5)
        config_layout.setContentsMargins(5, 5, 5, 5)
        
        # Prefix and Suffix in 2 columns side by side
        prefix_suffix_grid = QGridLayout()
        prefix_suffix_grid.setSpacing(8)
        
        prefix_label = QLabel("Prefix:")
        prefix_suffix_grid.addWidget(prefix_label, 0, 0)
        self.rename_prefix = QLineEdit()
        self.rename_prefix.setPlaceholderText("e.g., Dim_")
        prefix_suffix_grid.addWidget(self.rename_prefix, 0, 1)
        
        suffix_label = QLabel("Suffix:")
        prefix_suffix_grid.addWidget(suffix_label, 0, 2)
        self.rename_suffix = QLineEdit()
        self.rename_suffix.setPlaceholderText("e.g., _new")
        prefix_suffix_grid.addWidget(self.rename_suffix, 0, 3)
        
        config_layout.addLayout(prefix_suffix_grid)
        
        # Schema field (for SQL Server, Snowflake, Fabric)
        schema_layout = QHBoxLayout()
        schema_layout.setSpacing(8)
        schema_label = QLabel("Schema:")
        schema_label.setToolTip("Database schema for SQL Server, Snowflake, or Fabric (e.g., dbo, PUBLIC)")
        schema_layout.addWidget(schema_label)
        self.rename_schema = QLineEdit()
        self.rename_schema.setPlaceholderText("dbo or PUBLIC (for SQL Server, Snowflake, Fabric)")
        self.rename_schema.setText("dbo")  # Default to dbo
        schema_layout.addWidget(self.rename_schema)
        config_layout.addLayout(schema_layout)
        
        # Case Conversion dropdown
        case_label = QLabel("Case Conversion:")
        config_layout.addWidget(case_label)
        self.rename_transformation = QComboBox()
        self.rename_transformation.setMinimumHeight(28)
        self.rename_transformation.addItems([
            "None",
            "snake_to_pascal (snake_case → PascalCase)",
            "pascal_to_snake (PascalCase → snake_case)",
            "camel_to_pascal (camelCase → PascalCase)",
            "pascal_to_camel (PascalCase → camelCase)",
            "kebab_to_pascal (kebab-case → PascalCase)",
            "snake_to_camel (snake_case → camelCase)",
            "uppercase (UPPERCASE)",
            "lowercase (lowercase)",
            "title_case (Title Case)",
            "remove_spaces (Remove Spaces)",
            "spaces_to_underscores (Spaces → Underscores)",
            "remove_prefix (tbl_Customer → Customer)",
            "remove_suffix (CustomerTable → Customer)"
        ])
        config_layout.addWidget(self.rename_transformation)
        
        # Load Tables and Apply buttons in 2 columns side by side
        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(8)
        
        load_tables_btn = QPushButton(qta.icon('fa5s.download'), "Load Tables")
        load_tables_btn.setMinimumHeight(40)
        load_tables_btn.setStyleSheet("background: #16a085; color: white; padding: 8px 12px; font-weight: bold;")
        load_tables_btn.clicked.connect(self.load_tables_from_selected_models)
        buttons_grid.addWidget(load_tables_btn, 0, 0)
        
        apply_btn = QPushButton(qta.icon('fa5s.sync-alt'), "Apply to All")
        apply_btn.setMinimumHeight(40)
        apply_btn.setStyleSheet("background: #3498db; color: white; padding: 8px 12px; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_prefix_suffix_to_tables)
        buttons_grid.addWidget(apply_btn, 0, 1)
        
        config_layout.addLayout(buttons_grid)
        
        # Preview info
        self.rename_config_info = QLabel("💡 Load tables → apply prefix/suffix/case or edit names")
        self.rename_config_info.setStyleSheet("padding: 8px; border-radius: 3px; font-size: 11px;")
        self.rename_config_info.setWordWrap(True)
        config_layout.addWidget(self.rename_config_info)
        
        # Advanced option checkbox for backend table renaming
        self.rename_backend_table = QCheckBox("⚙️ Also rename backend table file (table definition file)")
        self.rename_backend_table.setChecked(True)  # Default to true for backward compatibility
        self.rename_backend_table.setToolTip(
            "Checked: Rename both display name and .tmdl file (backend table)\n"
            "Unchecked: Rename only display name, keep .tmdl file unchanged (UI only)"
        )
        config_layout.addWidget(self.rename_backend_table)
        
        config_group.setLayout(config_layout)
        left_layout.addWidget(config_group)
        
        content_layout.addWidget(left_container, 4)  # 40% width
        
        # ============ RIGHT SIDE: Table Preview (60%) ============
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Table Preview
        preview_group = QGroupBox("📋 Table Preview - Edit 'New Schema' and 'New Name' for Selective Renaming")
        preview_layout = QVBoxLayout()
        
        self.rename_table_preview = QTableWidget()
        self.rename_table_preview.setColumnCount(7)
        self.rename_table_preview.setHorizontalHeaderLabels(["Workspace", "Model", "Current Schema", "Current Name", "New Schema", "New Name", "Columns"])
        self.rename_table_preview.horizontalHeader().setStretchLastSection(False)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.rename_table_preview.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.rename_table_preview.setColumnWidth(0, 120)
        self.rename_table_preview.setColumnWidth(1, 180)
        self.rename_table_preview.setColumnWidth(2, 100)
        self.rename_table_preview.setColumnWidth(4, 100)
        self.rename_table_preview.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.rename_table_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.rename_table_preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        preview_layout.addWidget(self.rename_table_preview)
        
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)
        
        content_layout.addWidget(right_container, 6)  # 60% width
        
        main_layout.addLayout(content_layout)
        
        # Execute button
        rename_btn = QPushButton(qta.icon('fa5s.magic'), "Execute Bulk Rename")
        rename_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                padding: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        rename_btn.clicked.connect(self.execute_bulk_rename)
        main_layout.addWidget(rename_btn)
        
        # Progress bar
        self.rename_progress = QProgressBar()
        self.rename_progress.setVisible(False)
        self.rename_progress.setStyleSheet("QProgressBar { height: 25px; text-align: center; font-weight: bold; }")
        main_layout.addWidget(self.rename_progress)
        
        # Results
        self.rename_results = QTextEdit()
        self.rename_results.setReadOnly(True)
        self.rename_results.setMinimumHeight(120)
        self.rename_results.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background: #34495e; color: #ecf0f1; padding: 8px;")
        main_layout.addWidget(self.rename_results)
        
        self.tabs.addTab(tab, qta.icon('fa5s.edit', color=self._get_tab_icon_color()), "Rename Tables")
        
        # Initialize
        self.rename_models_data = []
    
    def create_column_rename_tab(self):
        """Create Column Rename tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with important note
        header_layout = QHBoxLayout()
        info_label = QLabel("🔤 Column Rename: Filter and rename columns with transformations (prefix/suffix, case conversions)")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        
        # Important note in header
        note_label = QLabel(
            "⚠️ <b>Important:</b> After renaming, close Power BI Desktop completely and reopen the .pbip file to see changes."
        )
        note_label.setWordWrap(False)
        note_label.setStyleSheet("""
            QLabel {
                background-color: #f39c12;
                color: #000;
                padding: 8px 12px;
                border-radius: 5px;
                font-size: 10px;
            }
        """)
        header_layout.addWidget(note_label)
        
        main_layout.addLayout(header_layout)
        
        # Top area: Filters, Transformation, and Advanced Options in horizontal layout
        top_area = QHBoxLayout()
        top_area.setSpacing(10)
        
        # ============ Filter Group (50% width) ============
        filter_group = QGroupBox("1️⃣ Filters")
        filter_layout = QGridLayout()
        filter_layout.setSpacing(8)
        filter_layout.setContentsMargins(8, 8, 8, 8)
        
        # Row 0: Scan button (full width)
        scan_col_btn = QPushButton(qta.icon('fa5s.sync'), "Scan Models")
        scan_col_btn.setMinimumHeight(28)
        scan_col_btn.setStyleSheet("background: #16a085; color: white; padding: 8px; font-weight: bold; font-size: 11px;")
        scan_col_btn.clicked.connect(self.scan_column_models)
        filter_layout.addWidget(scan_col_btn, 0, 0, 1, 4)
        
        # Row 1: Workspace and Semantic Model
        workspace_label = QLabel("Workspace:")
        workspace_label.setMinimumWidth(80)
        workspace_label.setMaximumWidth(100)
        filter_layout.addWidget(workspace_label, 1, 0)
        self.col_workspace_filter = QComboBox()
        self.col_workspace_filter.setMinimumHeight(26)
        self.col_workspace_filter.currentIndexChanged.connect(self.filter_column_tables)
        filter_layout.addWidget(self.col_workspace_filter, 1, 1)
        
        model_label = QLabel("Model:")
        model_label.setMinimumWidth(60)
        model_label.setMaximumWidth(80)
        filter_layout.addWidget(model_label, 1, 2)
        self.col_model_filter = QComboBox()
        self.col_model_filter.setMinimumHeight(26)
        self.col_model_filter.currentIndexChanged.connect(self.filter_column_tables)
        filter_layout.addWidget(self.col_model_filter, 1, 3)
        
        # Row 2: Table and Load button
        table_label = QLabel("Table:")
        table_label.setMinimumWidth(80)
        table_label.setMaximumWidth(100)
        filter_layout.addWidget(table_label, 2, 0)
        self.col_table_filter = QComboBox()
        self.col_table_filter.setMinimumHeight(26)
        self.col_table_filter.currentIndexChanged.connect(self.load_columns_for_selected_table)
        filter_layout.addWidget(self.col_table_filter, 2, 1)
        
        load_cols_btn = QPushButton(qta.icon('fa5s.download'), "Load Columns")
        load_cols_btn.setMinimumHeight(26)
        load_cols_btn.setStyleSheet("background: #3498db; color: white; padding: 6px; font-weight: bold;")
        load_cols_btn.clicked.connect(self.load_columns_for_selected_table)
        filter_layout.addWidget(load_cols_btn, 2, 2, 1, 2)
        
        filter_group.setLayout(filter_layout)
        top_area.addWidget(filter_group, 5)  # 50% width
        
        # ============ Transformation Group (50% width) ============
        transform_group = QGroupBox("2️⃣ Transformation")
        transform_layout = QGridLayout()
        transform_layout.setSpacing(8)
        transform_layout.setContentsMargins(8, 8, 8, 8)
        
        # Row 0: Prefix and Suffix
        prefix_label = QLabel("Prefix:")
        prefix_label.setMinimumWidth(60)
        prefix_label.setMaximumWidth(80)
        prefix_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        transform_layout.addWidget(prefix_label, 0, 0)
        self.col_prefix = QLineEdit()
        self.col_prefix.setMinimumHeight(26)
        self.col_prefix.setPlaceholderText("e.g., col_")
        transform_layout.addWidget(self.col_prefix, 0, 1)
        
        suffix_label = QLabel("Suffix:")
        suffix_label.setMinimumWidth(60)
        suffix_label.setMaximumWidth(80)
        suffix_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        transform_layout.addWidget(suffix_label, 0, 2)
        self.col_suffix = QLineEdit()
        self.col_suffix.setMinimumHeight(26)
        self.col_suffix.setPlaceholderText("e.g., _new")
        transform_layout.addWidget(self.col_suffix, 0, 3)
        
        # Row 1: Case Conversion (full width)
        case_label = QLabel("Case:")
        case_label.setMinimumWidth(60)
        case_label.setMaximumWidth(80)
        case_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        transform_layout.addWidget(case_label, 1, 0)
        self.col_transformation = QComboBox()
        self.col_transformation.setMinimumHeight(26)
        self.col_transformation.addItems([
            "None",
            "snake_to_pascal (snake_case → PascalCase)",
            "pascal_to_snake (PascalCase → snake_case)",
            "camel_to_pascal (camelCase → PascalCase)",
            "pascal_to_camel (PascalCase → camelCase)",
            "kebab_to_pascal (kebab-case → PascalCase)",
            "snake_to_camel (snake_case → camelCase)",
            "uppercase (UPPERCASE)",
            "lowercase (lowercase)",
            "title_case (Title Case)",
            "remove_spaces (Remove Spaces)",
            "spaces_to_underscores (Spaces → Underscores)",
            "remove_prefix (tbl_Customer → Customer)",
            "remove_suffix (CustomerTable → Customer)"
        ])
        transform_layout.addWidget(self.col_transformation, 1, 1, 1, 3)
        
        # Row 2: Advanced checkbox - sourceColumn (backend)
        self.col_rename_source = QCheckBox("⚙️ Also rename sourceColumn (backend/physical column)")
        self.col_rename_source.setChecked(False)
        transform_layout.addWidget(self.col_rename_source, 2, 0, 1, 4)
        
        # Row 3: Advanced checkbox - update visuals
        self.col_update_visuals = QCheckBox("📊 Also update report visual references (Entity, Property, queryRef, nativeQueryRef)")
        self.col_update_visuals.setChecked(True)
        transform_layout.addWidget(self.col_update_visuals, 3, 0, 1, 4)
        
        # Row 4: Apply transformation button (full width)
        apply_transform_btn = QPushButton(qta.icon('fa5s.sync-alt'), "Apply Transformation")
        apply_transform_btn.setMinimumHeight(28)
        apply_transform_btn.setStyleSheet("background: #e67e22; color: white; padding: 6px 10px; font-weight: bold; font-size: 11px;")
        apply_transform_btn.clicked.connect(self.apply_column_transformation)
        transform_layout.addWidget(apply_transform_btn, 4, 0, 1, 4)
        
        transform_group.setLayout(transform_layout)
        top_area.addWidget(transform_group, 5)  # 50% width
        
        # Add top area to main layout
        main_layout.addLayout(top_area)
        
        # ============ Column Preview Table (Full Width) ============
        preview_group = QGroupBox("📋 Column Preview - Edit 'New Name' for Selective Renaming")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        self.column_preview_table = QTableWidget()
        self.column_preview_table.setColumnCount(7)
        self.column_preview_table.setHorizontalHeaderLabels([
            "Workspace", "Model", "Table", "Current Name", "New Name", "Type", "Calculated"
        ])
        header = self.column_preview_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.column_preview_table.setColumnWidth(0, 120)
        self.column_preview_table.setColumnWidth(1, 150)
        self.column_preview_table.setColumnWidth(2, 150)
        self.column_preview_table.verticalHeader().setDefaultSectionSize(20)  # Compact row height
        self.column_preview_table.setMaximumHeight(200)
        self.column_preview_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.column_preview_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        preview_layout.addWidget(self.column_preview_table)
        
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)
        
        # Execute button
        execute_col_rename_btn = QPushButton(qta.icon('fa5s.magic'), "Execute Column Rename")
        execute_col_rename_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 5px;
                min-height: 28px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        execute_col_rename_btn.clicked.connect(self.execute_column_rename)
        main_layout.addWidget(execute_col_rename_btn)
        
        # Progress bar
        self.col_rename_progress = QProgressBar()
        self.col_rename_progress.setVisible(False)
        self.col_rename_progress.setStyleSheet("QProgressBar { height: 25px; text-align: center; font-weight: bold; }")
        main_layout.addWidget(self.col_rename_progress)
        
        # Results
        self.col_rename_results = QTextEdit()
        self.col_rename_results.setReadOnly(True)
        self.col_rename_results.setMinimumHeight(80)
        self.col_rename_results.setMaximumHeight(100)
        self.col_rename_results.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background: #2c3e50; color: #ecf0f1; padding: 8px;")
        main_layout.addWidget(self.col_rename_results)
        
        main_layout.addStretch()
        
        self.tabs.addTab(tab, qta.icon('fa5s.columns', color=self._get_tab_icon_color()), "Rename Columns")
        
    def create_upload_tab(self):
        """Create Upload to Fabric tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("📤 Upload to Fabric")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(header)
        
        layout.addWidget(QLabel("<hr>"))
        
        # Fabric CLI authentication status
        auth_group = QGroupBox("Fabric CLI Authentication")
        auth_layout = QHBoxLayout(auth_group)
        self.auth_status_label = QLabel("Status: Not Checked")
        self.auth_status_label.setStyleSheet("font-weight: bold;")
        auth_layout.addWidget(self.auth_status_label)
        auth_layout.addStretch()
        check_auth_btn = QPushButton(qta.icon('fa5s.key'), "Check Fabric CLI")
        check_auth_btn.clicked.connect(self.check_fabric_auth)
        auth_layout.addWidget(check_auth_btn)
        layout.addWidget(auth_group)
        
        layout.addWidget(QLabel("<hr>"))
        
        # Workspace selection
        workspace_group = QWidget()
        workspace_layout = QHBoxLayout(workspace_group)
        workspace_layout.addWidget(QLabel("Target Workspace:"))
        self.publish_workspace_input = QLineEdit()
        self.publish_workspace_input.setPlaceholderText("Enter Fabric workspace name...")
        workspace_layout.addWidget(self.publish_workspace_input, 1)
        layout.addWidget(workspace_group)
        
        # Model selection
        model_group = QWidget()
        model_layout = QHBoxLayout(model_group)
        model_layout.addWidget(QLabel("Select Model:"))
        self.publish_model_combo = QComboBox()
        self.publish_model_combo.currentIndexChanged.connect(self.load_publish_items)
        model_layout.addWidget(self.publish_model_combo, 1)
        scan_publish_btn = QPushButton(qta.icon('fa5s.search'), "Scan Models")
        scan_publish_btn.clicked.connect(self.scan_publish_models)
        model_layout.addWidget(scan_publish_btn)
        layout.addWidget(model_group)
        
        # Items to publish (checkboxes)
        items_label = QLabel("Items to Publish:")
        items_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(items_label)
        
        self.publish_items_widget = QWidget()
        self.publish_items_layout = QVBoxLayout(self.publish_items_widget)
        self.publish_items_layout.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(self.publish_items_widget)
        
        self.publish_checkboxes = []
        
        # Execute button
        publish_btn = QPushButton(qta.icon('fa5s.cloud-upload-alt'), "Publish to Fabric")
        publish_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        publish_btn.clicked.connect(self.execute_publish)
        layout.addWidget(publish_btn)
        
        # Progress bar
        self.publish_progress_bar = QProgressBar()
        self.publish_progress_bar.setVisible(False)
        self.publish_progress_bar.setTextVisible(True)
        self.publish_progress_bar.setFormat("%p% - %v/%m items")
        self.publish_progress_bar.setMinimumHeight(30)
        layout.addWidget(self.publish_progress_bar)
        
        # Results
        layout.addWidget(QLabel("Results:"))
        self.publish_results = QTextEdit()
        self.publish_results.setReadOnly(True)
        self.publish_results.setMaximumHeight(150)
        layout.addWidget(self.publish_results)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, qta.icon('fa5s.edit', color=self._get_tab_icon_color()), "Rename Tables")
    
    # OLD PUBLISH TAB - REMOVED (replaced by Upload to Fabric tab)
    # def create_publish_tab(self):
    #     """Create Publish to Fabric tab"""
    #     ...removed...
    
    def prepend_to_text_edit(self, text_edit: QTextEdit, message: str):
        """Helper to prepend text to QTextEdit (newest first)"""
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertText(f"{message}\n")
        text_edit.setTextCursor(cursor)
        
    def browse_export_folder(self):
        """Browse for export folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Power BI Export Folder",
            str(self.downloads_base)
        )
        
        if folder:
            self.export_path_input.setText(folder)
            # Sync to Upload to Fabric tab
            if hasattr(self, 'fabric_upload_tab'):
                self.fabric_upload_tab.set_folder_path(folder)
            
    def index_export(self):
        """Index the selected export folder"""
        # Try dropdown first, then manual input
        export_path = self.export_path_input.text()
        if not export_path and self.export_dropdown.currentText():
            export_path = self.export_dropdown.currentText()
        
        # Sync to Upload to Fabric tab
        if export_path and hasattr(self, 'fabric_upload_tab'):
            self.fabric_upload_tab.set_folder_path(export_path)
        
        if not export_path:
            QMessageBox.warning(self, "Warning", "Please select an export folder")
            return
            
        if not Path(export_path).exists():
            QMessageBox.warning(self, "Warning", "Selected folder does not exist")
            return
            
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        # Start worker thread
        self.index_worker = IndexWorker(export_path)
        self.index_worker.progress.connect(self.update_progress)
        self.index_worker.finished.connect(self.index_complete)
        self.index_worker.error.connect(self.index_error)
        self.index_worker.start()
        
    def update_progress(self, message):
        """Update progress message"""
        self.statusBar().showMessage(message)
    
    def index_complete(self, result):
        """Handle indexing completion"""
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Indexing complete")
        
        stats = result.get('stats', {})
        file_structure = result.get('file_structure', {})
        
        # Enhanced success message with file info
        msg = f"✅ Indexed successfully!\n\n"
        msg += f"📁 File Structure:\n"
        msg += f"  • Parsed {file_structure.get('total_tmdl_files', 0)} TMDL files\n"
        msg += f"  • Total size: {file_structure.get('total_size_mb', 0)} MB"
        
        if stats.get('errors'):
            msg += f"\n\n⚠️ Warnings: {len(stats['errors'])} issues (check logs)"
        
        QMessageBox.information(self, "Success", msg)
        self.load_assessment_dashboard()
    
    def create_kpi_card(self, title, value, color):
        """Create a KPI card widget"""
        card = QGroupBox()
        # Create gradient effect
        if color == "#3498db":
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3498db, stop:1 #2980b9)"
        elif color == "#9b59b6":
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9b59b6, stop:1 #8e44ad)"
        elif color == "#1abc9c":
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1abc9c, stop:1 #16a085)"
        else:
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e67e22, stop:1 #d35400)"
        
        card.setStyleSheet(f"""
            QGroupBox {{
                background: {gradient};
                border-radius: 12px;
                padding: 20px;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title.upper())
        title_label.setStyleSheet("""
            font-size: 11px; 
            font-weight: bold; 
            color: rgba(255, 255, 255, 0.9);
            letter-spacing: 1px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 42px; 
            font-weight: bold; 
            color: white;
            margin-top: 8px;
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName(f"kpi_{title.lower().replace(' ', '_')}")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()
        
        card.setLayout(layout)
        card.setMinimumHeight(120)
        card.setMaximumHeight(140)
        
        return card
    
    def load_assessment_dashboard(self):
        """Load comprehensive assessment dashboard data"""
        try:
            response = requests.get("http://127.0.0.1:8000/api/assessment-summary")
            if response.status_code == 200:
                data = response.json()
                self.populate_assessment_dashboard(data)
            else:
                QMessageBox.warning(self, "Warning", f"Failed to load dashboard: {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load dashboard:\n{str(e)}")
    
    def populate_assessment_dashboard(self, data):
        """Populate dashboard with assessment data"""
        overview = data.get('overview', {})
        datasets_analysis = data.get('datasets_analysis', [])
        workspaces = data.get('top_workspaces', [])
        
        # Store full data for filtering
        self.full_assessment_data = datasets_analysis
        
        # Calculate core metrics
        total_workspaces = overview.get('total_workspaces', 0)
        total_datasets = overview.get('total_datasets', 0)
        total_tables = overview.get('total_tables', 0)
        total_sources = overview.get('total_data_sources', 0)
        
        # Update filter labels with counts
        self.workspace_label.setText(f"Workspace ({total_workspaces})")
        self.dataset_label.setText(f"Dataset ({total_datasets})")
        self.source_label.setText(f"Source Type ({total_sources})")
        
        # Populate filter dropdowns
        self.populate_filters(datasets_analysis, workspaces)
        
        # Populate main details table
        self.populate_details_table(datasets_analysis)
        
        # Load all details by default (no filter) - only if export path is available
        manual_path = self.export_path_input.text().strip()
        export_path_str = manual_path if manual_path else self.export_dropdown.currentText()
        if export_path_str and Path(export_path_str).exists():
            self.load_all_table_details()
        
        self.statusBar().showMessage("Report updated successfully")
    
    def populate_filters(self, datasets_analysis, workspaces):
        """Populate filter dropdown options"""
        # Block signals to prevent triggering during population
        self.filter_workspace.blockSignals(True)
        self.filter_dataset.blockSignals(True)
        self.filter_source.blockSignals(True)
        self.filter_relationships.blockSignals(True)
        
        # Clear existing items (keep "All" option)
        self.filter_workspace.clear()
        self.filter_dataset.clear()
        self.filter_source.clear()
        
        # Add "All" options
        self.filter_workspace.addItem("All Workspaces")
        self.filter_dataset.addItem("All Datasets")
        self.filter_source.addItem("All Sources")
        
        # Populate workspaces
        workspace_names = set()
        for ws in workspaces:
            ws_name = ws.get('workspace_name', 'Unknown')
            if ws_name and ws_name != 'Unknown':
                workspace_names.add(ws_name)
        for ws_name in sorted(workspace_names):
            self.filter_workspace.addItem(ws_name)
        
        # Populate datasets
        dataset_names = set()
        for dataset in datasets_analysis:
            ds_name = dataset.get('dataset_name', 'Unknown')
            if ds_name and ds_name != 'Unknown':
                dataset_names.add(ds_name)
        for ds_name in sorted(dataset_names):
            self.filter_dataset.addItem(ds_name)
        
        # Populate source types
        source_types = set()
        for dataset in datasets_analysis:
            sources = dataset.get('source_types', []) or dataset.get('sources', []) or []
            if sources and isinstance(sources, list):
                if len(sources) > 0 and isinstance(sources[0], dict):
                    sources = [s.get('source_type', '') for s in sources if isinstance(s, dict) and s.get('source_type')]
                for src in sources:
                    if src:
                        source_types.add(src)
        for src_type in sorted(source_types):
            self.filter_source.addItem(src_type)
        
        # Populate relationship types from database
        try:
            from database.schema import FabricDatabase
            db = FabricDatabase()
            cursor = db.conn.cursor()
            cursor.execute('SELECT DISTINCT cardinality FROM relationships WHERE cardinality IS NOT NULL ORDER BY cardinality')
            cardinalities = [row[0] for row in cursor.fetchall()]
            db.conn.close()
            
            # Update dropdown with actual cardinality values from database
            current_selection = self.filter_relationships.currentText()
            self.filter_relationships.clear()
            self.filter_relationships.addItem("All")
            if cardinalities:
                self.filter_relationships.addItems(cardinalities)
            else:
                # Default options if no data in database yet
                self.filter_relationships.addItems(["one-to-many", "many-to-one", "one-to-one", "many-to-many"])
            
            # Restore selection if it still exists
            idx = self.filter_relationships.findText(current_selection)
            if idx >= 0:
                self.filter_relationships.setCurrentIndex(idx)
        except Exception as e:
            logging.warning(f"Could not populate relationship types: {e}")
        
        # Re-enable signals
        self.filter_workspace.blockSignals(False)
        self.filter_dataset.blockSignals(False)
        self.filter_source.blockSignals(False)
        self.filter_relationships.blockSignals(False)
    
    def populate_details_table(self, datasets_analysis=None, workspace_filter=None, dataset_filter=None, source_filter=None, table_filter=None, relationship_filter=None):
        """Populate the main details tree with comprehensive dataset information - Direct DB query with filters"""
        self.details_table.clear()
        self.details_table.setHeaderLabels([
            "Workspace / Dataset / Table",
            "Hidden",
            "Columns",
            "Source Types",
            "Partitions"
        ])
        
        try:
            # Direct database query for better performance and accuracy
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # Build WHERE clause for filters
            where_conditions = []
            params = []
            
            # Apply workspace filter
            if workspace_filter and workspace_filter != "All Workspaces":
                where_conditions.append('w.workspace_name = ?')
                params.append(workspace_filter)
            
            # Apply dataset filter
            if dataset_filter and dataset_filter != "All Datasets":
                where_conditions.append('d.dataset_name = ?')
                params.append(dataset_filter)
            
            # Apply source type filter
            if source_filter and source_filter != "All Sources":
                where_conditions.append('EXISTS (SELECT 1 FROM data_sources ds2 WHERE ds2.object_id = do.object_id AND ds2.source_type = ?)')
                params.append(source_filter)
            
            # Apply table name filter (partial match)
            if table_filter:
                where_conditions.append('do.object_name LIKE ?')
                params.append(f'%{table_filter}%')
            
            # Query to get all tables with their dataset and workspace info, plus data sources
            query = '''
                SELECT 
                    w.workspace_name,
                    d.dataset_name,
                    do.object_name as table_name,
                    do.column_count,
                    (SELECT COUNT(*) FROM relationships r WHERE r.from_object_id = do.object_id OR r.to_object_id = do.object_id) as relationship_count,
                    (SELECT COUNT(*) FROM measures m WHERE m.object_id = do.object_id) as measure_count,
                    COUNT(DISTINCT ds.source_id) as data_source_count,
                    GROUP_CONCAT(DISTINCT ds.source_type) as source_types,
                    CASE WHEN do.is_hidden = 1 THEN 'Yes' ELSE 'No' END as is_hidden,
                    do.last_modified,
                    do.partition_count,
                    d.dataset_id,
                    w.workspace_id
                FROM data_objects do
                JOIN datasets d ON do.dataset_id = d.dataset_id
                JOIN workspaces w ON d.workspace_id = w.workspace_id
                LEFT JOIN data_sources ds ON do.object_id = ds.object_id
            '''
            
            if where_conditions:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            query += '''
                GROUP BY do.object_id
                ORDER BY w.workspace_name, d.dataset_name, do.object_name
            '''
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            
            # Build hierarchical structure: Workspace -> Dataset -> Tables
            workspace_items = {}  # workspace_name -> QTreeWidgetItem
            dataset_items = {}    # (workspace_name, dataset_name) -> QTreeWidgetItem
            
            # Apply relationship filter and build tree
            for row in rows:
                row_dict = dict(row)
                
                # Apply relationship filter
                if relationship_filter and relationship_filter != "All":
                    rel_count = row_dict.get('relationship_count', 0) or 0
                    if relationship_filter == "With Relationships" and rel_count == 0:
                        continue
                    elif relationship_filter == "Without Relationships" and rel_count > 0:
                        continue
                
                workspace_name = row_dict['workspace_name'] or '-'
                dataset_name = row_dict['dataset_name'] or '-'
                table_name = row_dict['table_name'] or '-'
                
                # Create or get workspace item
                if workspace_name not in workspace_items:
                    ws_item = QTreeWidgetItem(self.details_table, [f"📁 {workspace_name}", "", "", "", ""])
                    ws_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'workspace',
                        'workspace_id': row_dict['workspace_id'],
                        'workspace_name': workspace_name
                    })
                    ws_item.setExpanded(True)  # Expand by default
                    font = ws_item.font(0)
                    font.setBold(True)
                    ws_item.setFont(0, font)
                    workspace_items[workspace_name] = ws_item
                
                # Create or get dataset item
                dataset_key = (workspace_name, dataset_name)
                if dataset_key not in dataset_items:
                    ds_item = QTreeWidgetItem(workspace_items[workspace_name], [f"📊 {dataset_name}", "", "", "", ""])
                    ds_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'dataset',
                        'workspace_id': row_dict['workspace_id'],
                        'dataset_id': row_dict['dataset_id'],
                        'dataset_name': dataset_name,
                        'workspace_name': workspace_name
                    })
                    ds_item.setExpanded(True)  # Expand by default
                    font = ds_item.font(0)
                    font.setBold(True)
                    ds_item.setFont(0, font)
                    dataset_items[dataset_key] = ds_item
                
                # Create table item
                is_hidden = row_dict['is_hidden'] or 'No'
                source_types = row_dict['source_types'] or 'None'
                if source_types and source_types != 'None':
                    # Limit display to avoid long strings
                    types_list = source_types.split(',')
                    if len(types_list) > 3:
                        source_types = ', '.join(types_list[:3]) + f' (+{len(types_list)-3})'
                
                partition_count = row_dict['partition_count'] or 0
                partition_text = str(partition_count) if partition_count > 0 else '-'
                
                table_item = QTreeWidgetItem(dataset_items[dataset_key], [
                    f"📋 {table_name}",
                    is_hidden,
                    str(row_dict['column_count'] or 0),
                    source_types,
                    partition_text
                ])
                
                # Store data for selection handling
                table_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'table',
                    'workspace_id': row_dict['workspace_id'],
                    'dataset_id': row_dict['dataset_id'],
                    'table_name': table_name,
                    'workspace_name': workspace_name,
                    'dataset_name': dataset_name
                })
                
                # Color for hidden tables
                if is_hidden == 'Yes':
                    table_item.setForeground(1, QColor(255, 165, 0))  # Orange for hidden
            
            db.conn.close()
            
        except Exception as e:
            logging.error(f"Error populating details table: {e}", exc_info=True)
            # Fallback to empty table
            pass
        
        # Resize columns to content
        for i in range(self.details_table.columnCount()):
            self.details_table.resizeColumnToContents(i)
    
    def load_all_table_details(self, workspace_filter=None, dataset_filter=None, source_filter=None, table_search=None, relationship_type=None):
        """Load all table details without filtering by specific table - from database"""
        try:
            from pathlib import Path
            
            # Load all details from database (no file parsing needed)
            logging.info(f"Loading all table details from database with filters: workspace={workspace_filter}, dataset={dataset_filter}, source={source_filter}, table_search={table_search}")
            
            # Load ALL relationships, measures, columns with filters (pass None for parser/paths since we're loading from DB)
            self.load_relationships(None, Path("."), "", None, workspace_filter, dataset_filter, source_filter, table_search, relationship_type)
            self.load_measures(None, Path("."), None, workspace_filter, dataset_filter, source_filter, table_search)
            self.load_columns(None, Path("."), None, workspace_filter, dataset_filter, source_filter, table_search)
            
            # Clear Power Query (show message instead)
            self.powerquery_text.setPlainText("Select a specific table to view its Power Query M code")
            
            # Update label and show the detail panel
            self.selected_table_label.setText("All Tables")
            self.detail_panel.setVisible(True)
            logging.info("Loaded all table details with filters applied")
            
        except Exception as e:
            logging.error(f"Error loading all table details: {e}", exc_info=True)
    
    def unselect_and_show_all(self, item=None, column=None):
        """Unselect current row and show all table details"""
        try:
            self.details_table.clearSelection()
            self.load_all_table_details()
            logging.info("Unselected table and showing all details")
        except Exception as e:
            logging.error(f"Error unselecting table: {e}", exc_info=True)
    
    def on_table_row_selected(self):
        """Handle row selection in details tree to show detailed information"""
        try:
            selected_items = self.details_table.selectedItems()
            if not selected_items:
                # No selection - load all details
                self.load_all_table_details()
                return
            
            # Get the selected item
            current_item = self.details_table.currentItem()
            
            if not current_item:
                logging.warning("No current item found")
                return
            
            data = current_item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                logging.warning("No user data found in item")
                return
            
            item_type = data.get('type')
            
            # Only load details for table items, not workspace/dataset groups
            if item_type == 'table':
                workspace_id = data.get('workspace_id')
                dataset_id = data.get('dataset_id')
                table_name = data.get('table_name')
                
                logging.info(f"Loading details for: workspace={workspace_id}, dataset={dataset_id}, table={table_name}")
                
                # Update selected table label
                self.selected_table_label.setText(f"Selected Table: {table_name}")
                
                # Load and display details for selected table only
                self.load_table_details(workspace_id, dataset_id, table_name)
                self.detail_panel.setVisible(True)
            else:
                # For workspace/dataset items, show all details
                self.load_all_table_details()
            
        except Exception as e:
            logging.error(f"Error in on_table_row_selected: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to load table details: {str(e)}")
    
    def load_table_details(self, workspace_id: str, dataset_id: str, table_name: str):
        """Load detailed information for selected table"""
        try:
            from pathlib import Path
            from parsers import PowerBIParser
            
            # Get the export folder path - prefer manual path over dropdown
            manual_path = self.export_path_input.text().strip()
            export_path_str = manual_path if manual_path else self.export_dropdown.currentText()
            
            if not export_path_str:
                self.powerquery_text.setPlainText("No export folder selected")
                logging.warning("No export folder selected")
                return
            
            export_path = Path(export_path_str)
            if not export_path.exists():
                self.powerquery_text.setPlainText(f"Export folder not found: {export_path_str}")
                logging.warning(f"Export path does not exist: {export_path_str}")
                return
            
            logging.info(f"Export path: {export_path}")
            
            # Find the workspace and dataset folders
            workspace_folder = None
            dataset_folder = None
            
            # Check Raw Files structure
            if (export_path / "Raw Files").exists():
                search_root = export_path / "Raw Files"
            else:
                search_root = export_path
            
            logging.info(f"Search root: {search_root}")
            
            # Extract workspace name from workspace_id
            # Format: powerbi_WorkspaceName_timestamp
            parts = workspace_id.split('_')
            if len(parts) >= 2:
                workspace_name = parts[1]
            else:
                workspace_name = None
                
            # Extract dataset name from dataset_id
            # Format: powerbi_WorkspaceName_timestamp_DatasetName
            dataset_name = dataset_id.split('_')[-1] if '_' in dataset_id else None
            
            logging.info(f"Looking for workspace: {workspace_name}, dataset: {dataset_name}")
            
            # Find matching folders
            for ws_folder in search_root.iterdir():
                if not ws_folder.is_dir():
                    continue
                    
                if workspace_name and workspace_name in ws_folder.name:
                    workspace_folder = ws_folder
                    logging.info(f"Found workspace folder: {ws_folder}")
                    
                    for ds_folder in ws_folder.glob("*.SemanticModel"):
                        if dataset_name and dataset_name in ds_folder.name:
                            dataset_folder = ds_folder
                            logging.info(f"Found dataset folder: {ds_folder}")
                            break
                    break
            
            if not dataset_folder:
                msg = f"Dataset folder not found.\nWorkspace: {workspace_name}\nDataset: {dataset_name}\nSearch root: {search_root}"
                self.powerquery_text.setPlainText(msg)
                logging.warning(msg)
                return
            
            parser = PowerBIParser()
            
            # Load relationships
            self.load_relationships(parser, dataset_folder, dataset_id, table_name)
            
            # Load measures
            self.load_measures(parser, dataset_folder, table_name)
            
            # Load columns
            self.load_columns(parser, dataset_folder, table_name)
            
            # Load Power Query M code
            self.load_powerquery(parser, dataset_folder, table_name)
            
            logging.info("Successfully loaded all table details")
            
        except Exception as e:
            error_msg = f"Error loading table details: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.powerquery_text.setPlainText(error_msg)
    
    def load_relationships(self, parser, dataset_folder: Path, dataset_id: str, table_name: str = None,
                          workspace_filter: str = None, dataset_filter: str = None, source_filter: str = None,
                          table_search: str = None, relationship_type: str = None):
        """Load relationships from database (if table_name is None, load all)"""
        self.relationships_table.setRowCount(0)
        
        try:
            from services.detail_loader import DetailLoader
            
            relationships = DetailLoader.load_relationships(table_name, workspace_filter, dataset_filter, source_filter, table_search, relationship_type)
            logging.info(f"Found {len(relationships)} relationships" + (f" for table {table_name}" if table_name else ""))
            
            if relationships:
                logging.info(f"Sample relationship data: {relationships[0]}")
            
            for rel in relationships:
                row = self.relationships_table.rowCount()
                self.relationships_table.insertRow(row)
                
                self.relationships_table.setItem(row, 0, QTableWidgetItem(str(rel.get('workspace', '-'))))
                self.relationships_table.setItem(row, 1, QTableWidgetItem(str(rel.get('dataset', '-'))))
                self.relationships_table.setItem(row, 2, QTableWidgetItem(str(rel.get('from_table', '-'))))
                self.relationships_table.setItem(row, 3, QTableWidgetItem(str(rel.get('from_column', '-'))))
                self.relationships_table.setItem(row, 4, QTableWidgetItem(str(rel.get('to_table', '-'))))
                self.relationships_table.setItem(row, 5, QTableWidgetItem(str(rel.get('to_column', '-'))))
                self.relationships_table.setItem(row, 6, QTableWidgetItem(str(rel.get('cardinality', 'many-to-one'))))
                self.relationships_table.setItem(row, 7, QTableWidgetItem('Yes' if rel.get('is_active') else 'No'))
            
            if not relationships:
                self.relationships_table.insertRow(0)
                msg = "No relationships found" if not table_name else f"No relationships found for table {table_name}"
                self.relationships_table.setItem(0, 0, QTableWidgetItem(msg))
                logging.info(msg)
            
        except Exception as e:
            logging.error(f"Error loading relationships: {e}", exc_info=True)
    
    def load_measures(self, parser, dataset_folder: Path, table_name: str = None,
                     workspace_filter: str = None, dataset_filter: str = None, source_filter: str = None,
                     table_search: str = None):
        """Load measures from database (if table_name is None, load all)"""
        self.measures_table.setRowCount(0)
        
        try:
            from services.detail_loader import DetailLoader
            
            measures = DetailLoader.load_measures(table_name, workspace_filter, dataset_filter, source_filter, table_search)
            logging.info(f"Found {len(measures)} measures" + (f" for table {table_name}" if table_name else ""))
            
            if measures:
                logging.info(f"Sample measure data: {measures[0]}")
            
            for measure in measures:
                row = self.measures_table.rowCount()
                self.measures_table.insertRow(row)
                
                self.measures_table.setItem(row, 0, QTableWidgetItem(str(measure.get('workspace', '-'))))
                self.measures_table.setItem(row, 1, QTableWidgetItem(str(measure.get('dataset', '-'))))
                self.measures_table.setItem(row, 2, QTableWidgetItem(str(measure.get('measure_name', '-'))))
                
                # Truncate long expressions
                expression = measure.get('expression', '')
                if len(expression) > 100:
                    expression = expression[:100] + "..."
                self.measures_table.setItem(row, 3, QTableWidgetItem(expression))
                
                self.measures_table.setItem(row, 4, QTableWidgetItem(str(measure.get('format_string', '-') or '-')))
                self.measures_table.setItem(row, 5, QTableWidgetItem('Yes' if measure.get('is_hidden') else 'No'))
            
            if not measures:
                self.measures_table.insertRow(0)
                msg = "No measures found" if not table_name else f"No measures found for table {table_name}"
                self.measures_table.setItem(0, 0, QTableWidgetItem(msg))
                logging.info(msg)
            
        except Exception as e:
            logging.error(f"Error loading measures: {e}", exc_info=True)
    
    def load_columns(self, parser, dataset_folder: Path, table_name: str = None,
                    workspace_filter: str = None, dataset_filter: str = None, source_filter: str = None,
                    table_search: str = None):
        """Load columns from database (if table_name is None, load all from all tables)"""
        self.columns_table.setRowCount(0)
        
        try:
            from services.detail_loader import DetailLoader
            
            columns = DetailLoader.load_columns(table_name, workspace_filter, dataset_filter, source_filter, table_search)
            logging.info(f"Found {len(columns)} columns" + (f" for table {table_name}" if table_name else " (all tables)"))
            
            if columns:
                logging.info(f"Sample column data: {columns[0]}")
            
            for col in columns:
                row = self.columns_table.rowCount()
                self.columns_table.insertRow(row)
                
                self.columns_table.setItem(row, 0, QTableWidgetItem(str(col.get('workspace', '-'))))
                self.columns_table.setItem(row, 1, QTableWidgetItem(str(col.get('dataset', '-'))))
                self.columns_table.setItem(row, 2, QTableWidgetItem(str(col.get('table_name', '-'))))
                self.columns_table.setItem(row, 3, QTableWidgetItem(str(col.get('column_name', '-'))))
                self.columns_table.setItem(row, 4, QTableWidgetItem(str(col.get('data_type', '-'))))
                self.columns_table.setItem(row, 5, QTableWidgetItem(str(col.get('format_string', '-'))))
                self.columns_table.setItem(row, 6, QTableWidgetItem(str(col.get('source_column', '-'))))
                self.columns_table.setItem(row, 7, QTableWidgetItem('Yes' if col.get('is_hidden') else 'No'))
            
            if not columns:
                self.columns_table.insertRow(0)
                self.columns_table.setItem(0, 0, QTableWidgetItem("No columns found"))
                logging.warning("No columns found")
            
        except Exception as e:
            logging.error(f"Error loading columns: {e}", exc_info=True)
    
    def load_powerquery(self, parser, dataset_folder: Path, table_name: str):
        """Load Power Query M code from database"""
        try:
            from services.detail_loader import DetailLoader
            
            m_code = DetailLoader.load_power_query(table_name)
            logging.info(f"Loaded M code length: {len(m_code) if m_code else 0}")
            
            if m_code:
                self.powerquery_text.setPlainText(m_code)
                logging.info("Successfully loaded Power Query code")
            else:
                self.powerquery_text.setPlainText("No Power Query code found for this table")
                logging.info("No Power Query code found")
                
        except Exception as e:
            logging.error(f"Error loading Power Query: {e}", exc_info=True)
            self.powerquery_text.setPlainText(f"Error loading Power Query: {str(e)}")
    
    def apply_filters(self):
        """Apply selected filters to the details table and detail panel"""
        workspace_filter = self.filter_workspace.currentText()
        dataset_filter = self.filter_dataset.currentText()
        source_filter = self.filter_source.currentText()
        table_filter = self.filter_table.text().strip()
        relationship_filter = self.filter_relationships.currentText()
        
        # Check if any filter is active
        filters_active = (
            workspace_filter != "All Workspaces" or
            dataset_filter != "All Datasets" or
            source_filter != "All Sources" or
            table_filter != "" or
            relationship_filter != "All"
        )
        
        # Enable/disable Clear button and change color based on filter state
        self.clear_filters_btn.setEnabled(filters_active)
        if filters_active:
            # Active filters - highlight with blue color
            self.clear_filters_btn.setStyleSheet("background: #3498db; color: white; padding: 3px 8px; font-weight: bold;")
        else:
            # No filters - disabled gray
            self.clear_filters_btn.setStyleSheet("background: #bdc3c7; color: white; padding: 3px 8px; font-weight: bold;")
        
        # Repopulate LEFT table with filters applied
        self.populate_details_table(
            workspace_filter=workspace_filter if workspace_filter != "All Workspaces" else None,
            dataset_filter=dataset_filter if dataset_filter != "All Datasets" else None,
            source_filter=source_filter if source_filter != "All Sources" else None,
            table_filter=table_filter if table_filter else None,
            relationship_filter=relationship_filter if relationship_filter != "All" else None
        )
        
        # Always reload the detail panel with filters (right side) - regardless of selection
        # Get the current filter values to pass
        ws_filter = workspace_filter if workspace_filter != "All Workspaces" else None
        ds_filter = dataset_filter if dataset_filter != "All Datasets" else None
        src_filter = source_filter if source_filter != "All Sources" else None
        
        # Get relationship type filter
        rel_type_filter = relationship_filter if relationship_filter != "All" else None
        
        # Check if a specific table is selected
        selected_items = self.details_table.selectedItems()
        if selected_items:
            # Get the current item
            current_item = self.details_table.currentItem()
            if current_item:
                data = current_item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('type') == 'table':
                    table_name = data.get('table_name')
                    if table_name:
                        # Reload specific table details with filters applied
                        self.load_relationships(None, Path("."), "", table_name, ws_filter, ds_filter, src_filter, table_filter, rel_type_filter)
                        self.load_measures(None, Path("."), table_name, ws_filter, ds_filter, src_filter, table_filter)
                        self.load_columns(None, Path("."), table_name, ws_filter, ds_filter, src_filter, table_filter)
                else:
                    # Workspace or dataset selected - show all
                    self.load_all_table_details(ws_filter, ds_filter, src_filter, table_filter, rel_type_filter)
        else:
            # No table selected - reload all details with filters
            self.load_all_table_details(ws_filter, ds_filter, src_filter, table_filter, rel_type_filter)
        
        # Update status - count only table items (not workspace/dataset groups)
        total_tables = 0
        for i in range(self.details_table.topLevelItemCount()):
            ws_item = self.details_table.topLevelItem(i)
            for j in range(ws_item.childCount()):
                ds_item = ws_item.child(j)
                total_tables += ds_item.childCount()
        self.statusBar().showMessage(f"Showing {total_tables} tables")
    
    def clear_filters(self):
        """Clear all filter selections"""
        self.filter_workspace.setCurrentIndex(0)
        self.filter_dataset.setCurrentIndex(0)
        self.filter_source.setCurrentIndex(0)
        self.filter_table.clear()
        self.filter_relationships.setCurrentIndex(0)
        self.apply_filters()
    
    def clear_database(self):
        """Clear all data from database and delete backup files"""
        reply = QMessageBox.question(
            self, 
            "Clear Database",
            "Are you sure you want to delete ALL indexed data from the database?\n\n"
            "This will remove:\n"
            "• All workspaces\n"
            "• All datasets\n"
            "• All tables and data sources\n"
            "• All migration history\n"
            "• All backup files\n"
            "• All database backup files (.db, .db-shm, .db-wal)\n\n"
            "This action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from pathlib import Path
            import shutil
            import os
            
            # Call API to clear database
            response = requests.post(f"{self.api_base}/api/clear-database")
            
            if response.status_code == 200:
                # Delete database backup files (skip files in use)
                db_backups_deleted = 0
                db_backups_skipped = 0
                
                try:
                    # Get database directory from AppData
                    appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~/.local/share'))
                    db_dir = Path(appdata) / 'PowerBI Migration Toolkit' / 'data'
                    
                    if db_dir.exists():
                        # Delete all database backup files (fabric_migration_backup_*.db)
                        for db_file in db_dir.glob('fabric_migration_backup_*.db'):
                            try:
                                db_file.unlink()
                                db_backups_deleted += 1
                            except (PermissionError, OSError):
                                # Skip files that are in use or locked
                                db_backups_skipped += 1
                        
                        # Also delete WAL and SHM files (skip if in use)
                        for ext in ['.db-shm', '.db-wal']:
                            for wal_file in db_dir.glob(f'fabric_migration*{ext}'):
                                try:
                                    wal_file.unlink()
                                    db_backups_deleted += 1
                                except (PermissionError, OSError):
                                    # Skip files that are in use or locked
                                    db_backups_skipped += 1
                except Exception:
                    # Silently skip if directory access fails
                    pass
                
                # Also delete all BACKUP folders in export directories
                backup_deleted = False
                backup_error = None
                
                # Get current export path to find BACKUP folder
                export_path = self.export_path_input.text() or self.export_dropdown.currentText()
                if export_path:
                    export_path = Path(export_path)
                    
                    # Find export root (containing Raw Files or FabricExport_)
                    current = export_path
                    max_depth = 10
                    depth = 0
                    export_root = None
                    
                    while current.parent != current and depth < max_depth:
                        if (current / "Raw Files").exists() or current.name.startswith("FabricExport_"):
                            export_root = current
                            break
                        current = current.parent
                        depth += 1
                    
                    # Delete BACKUP folder if found
                    if export_root:
                        backup_root = export_root / "BACKUP"
                        if backup_root.exists():
                            try:
                                shutil.rmtree(backup_root)
                                backup_deleted = True
                            except Exception as e:
                                backup_error = str(e)
                
                # Show success message
                message = "Database cleared successfully!"
                
                if db_backups_deleted > 0:
                    message += f"\n{db_backups_deleted} database backup file(s) deleted."
                
                if db_backups_skipped > 0:
                    message += f"\n{db_backups_skipped} file(s) skipped (currently in use)."
                
                if backup_deleted:
                    message += "\nAll BACKUP folders have been deleted."
                    
                if backup_error:
                    message += f"\n\nWarning: Could not delete BACKUP folder:\n{backup_error}"
                
                QMessageBox.information(self, "Success", message)
                self.load_assessment_dashboard()  # Refresh dashboard to show empty state
                self.statusBar().showMessage("Database and backups cleared")
            else:
                QMessageBox.critical(self, "Error", f"Failed to clear database: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear database:\n{str(e)}")
    
    def export_database_to_excel(self):
        """Export all database tables to Excel file with multiple sheets"""
        try:
            from database.schema import FabricDatabase
            import pandas as pd
            from datetime import datetime
            from PyQt6.QtWidgets import QFileDialog
            
            # Ask user for save location
            default_filename = f"PowerBI_Assessment_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Database to Excel",
                default_filename,
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Ensure .xlsx extension
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            # Connect to database
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # List of tables to export
            tables = [
                'workspaces',
                'datasets', 
                'data_objects',
                'columns',
                'relationships',
                'measures',
                'power_query'
            ]
            
            # Create Excel writer
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for table_name in tables:
                    try:
                        # Get all data from table
                        query = f'SELECT * FROM {table_name}'
                        df = pd.read_sql_query(query, db.conn)
                        
                        # Write to Excel sheet (Excel sheet names are limited to 31 chars)
                        sheet_name = table_name[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        logging.info(f"Exported {len(df)} rows from {table_name}")
                    except Exception as e:
                        logging.error(f"Error exporting table {table_name}: {e}")
            
            db.conn.close()
            
            # Show success message
            QMessageBox.information(
                self,
                "Export Complete",
                f"Database exported successfully!\n\n"
                f"Location: {file_path}\n"
                f"Tables exported: {len(tables)}"
            )
            
            self.statusBar().showMessage(f"Database exported to {file_path}")
            
        except ImportError:
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "pandas and openpyxl libraries are required for Excel export.\n\n"
                "Install with: pip install pandas openpyxl"
            )
        except Exception as e:
            logging.error(f"Error exporting database: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Error", f"Failed to export database:\n{str(e)}")
        
    def index_error(self, error):
        """Handle indexing error"""
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Indexing failed")
        QMessageBox.critical(self, "Error", f"Indexing failed:\n{error}")
        
    def load_workspaces(self):
        """Load workspaces from API"""
        try:
            response = requests.get(f"{self.api_base}/api/workspaces")
            if response.status_code == 200:
                workspaces = response.json()
                self.populate_workspaces_table(workspaces)
            else:
                self.statusBar().showMessage("Failed to load workspaces")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load workspaces:\n{str(e)}")
            
    def populate_workspaces_table(self, workspaces):
        """Populate workspaces table"""
        self.workspaces_table.setRowCount(len(workspaces))
        
        for i, ws in enumerate(workspaces):
            self.workspaces_table.setItem(i, 0, QTableWidgetItem(ws['workspace_name']))
            self.workspaces_table.setItem(i, 1, QTableWidgetItem(ws['tool_id']))
            # Calculate total items from datasets + tables
            items = ws.get('dataset_count', 0) + ws.get('table_count', 0)
            self.workspaces_table.setItem(i, 2, QTableWidgetItem(str(items)))
            
        self.workspaces_table.resizeColumnsToContents()
        
    def scan_migration_models(self):
        """Scan for semantic models from database (indexed models from Assessment tab)"""
        try:
            from database.schema import FabricDatabase
            
            # Query database for all datasets with their paths
            db = FabricDatabase()
            cursor = db.conn.cursor()
            
            # Get all datasets with workspace info
            cursor.execute('''
                SELECT DISTINCT
                    w.workspace_name,
                    ds.dataset_name,
                    ds.file_path,
                    ds.dataset_id
                FROM datasets ds
                JOIN workspaces w ON ds.workspace_id = w.workspace_id
                WHERE ds.file_path IS NOT NULL
                ORDER BY w.workspace_name, ds.dataset_name
            ''')
            
            results = cursor.fetchall()
            
            if not results:
                db.conn.close()
                QMessageBox.warning(self, "Warning", "No indexed models found. Please index an export first in Assessment tab")
                return
            
            # Prepare data structures - DON'T close DB yet
            self.migration_models_table.setRowCount(0)
            self.migration_models_data = []
            
            # Populate table with models
            for workspace_name, dataset_name, file_path, dataset_id in results:
                try:
                    model_path = Path(file_path)
                    
                    # Get sources from database (already indexed)
                    # Use GROUP BY to handle duplicate data_sources entries
                    cursor.execute('''
                        SELECT 
                            MIN(ds.source_id) as source_id,
                            ds.source_type,
                            ds.server,
                            ds.database_name,
                            ds.connection_string,
                            o.object_name
                        FROM data_sources ds
                        JOIN data_objects o ON ds.object_id = o.object_id
                        WHERE o.dataset_id = ? AND o.object_type = 'Table'
                        GROUP BY ds.source_type, ds.server, ds.database_name, o.object_name
                    ''', (dataset_id,))
                    
                    db_sources = cursor.fetchall()
                    
                    # Group sources by server+database (one source per unique connection)
                    from collections import defaultdict
                    grouped_sources = defaultdict(list)
                    
                    for source_id, source_type, server, database, conn_str, table_name in db_sources:
                        key = (source_type, server, database, conn_str)
                        
                        # Read the actual M query from the table file to preserve transformations
                        table_file = model_path / "definition" / "tables" / f"{table_name}.tmdl"
                        m_query = None
                        if table_file.exists():
                            try:
                                content = table_file.read_text(encoding='utf-8')
                                # Extract M query from partition source section
                                import re
                                match = re.search(r'source\s*=\s*\n(.*?)(?=\n\n|\npartition|\nannotation PBI_ResultType|\Z)', content, re.DOTALL)
                                if match:
                                    m_query = match.group(1).strip()
                            except Exception:
                                pass  # If extraction fails, migration will use template
                        
                        # Get schema from Rename Tables tab if available, otherwise use default
                        default_schema = self.rename_schema.text().strip() if hasattr(self, 'rename_schema') and self.rename_schema.text().strip() else 'dbo'
                        grouped_sources[key].append({
                            'name': table_name,
                            'schema': default_schema,  # Use schema from Rename Tables tab
                            'm_query': m_query  # Include original M query
                        })
                    
                    # Convert grouped sources to list format expected by preview_migration
                    sources = []
                    for (source_type, server, database, conn_str), tables in grouped_sources.items():
                        sources.append({
                            'source_type': source_type,
                            'server': server,
                            'database': database,
                            'connection_string': conn_str,
                            'connection_details': {
                                'server': server,
                                'database': database
                            },
                            'tables': tables  # List of table dictionaries with 'name' and 'schema'
                        })
                    
                    source_count = sum(len(s['tables']) for s in sources)  # Count total tables
                    
                    # Store model data
                    self.migration_models_data.append({
                        'path': str(model_path),
                        'name': dataset_name,
                        'workspace': workspace_name,
                        'sources': sources,
                        'source_count': source_count
                    })
                    
                    # Add to table
                    row = self.migration_models_table.rowCount()
                    self.migration_models_table.insertRow(row)
                    
                    # Checkbox
                    checkbox_item = QTableWidgetItem()
                    checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    checkbox_item.setCheckState(Qt.CheckState.Unchecked)
                    self.migration_models_table.setItem(row, 0, checkbox_item)
                    
                    # Workspace name
                    workspace_item = QTableWidgetItem(workspace_name)
                    self.migration_models_table.setItem(row, 1, workspace_item)
                    
                    # Model name
                    name_item = QTableWidgetItem(dataset_name)
                    name_item.setToolTip(str(model_path))  # Show full path on hover
                    self.migration_models_table.setItem(row, 2, name_item)
                    
                    # Source count
                    source_item = QTableWidgetItem(str(source_count))
                    source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.migration_models_table.setItem(row, 3, source_item)
                    
                except Exception as e:
                    logging.error(f"Error processing model {dataset_name}: {e}")
            
            # Close database connection after all queries are done
            db.conn.close()
            
            self.migration_models_table.resizeColumnsToContents()
            self.statusBar().showMessage(f"Found {len(self.migration_models_data)} indexed semantic model(s)")
            
            # Update filter options based on detected source types
            self.update_migration_filters()
            
        except Exception as e:
            logging.error(f"Error scanning migration models: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to scan models: {str(e)}")
    
    def update_migration_filters(self):
        """Dynamically update filter checkboxes based on detected source types in all models"""
        # Clear existing filter widgets
        while self.migration_filter_layout.count():
            item = self.migration_filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.migration_models_data:
            # Show placeholder if no models
            self.migration_filter_placeholder = QLabel("📋 Scan models to see available source types")
            self.migration_filter_placeholder.setStyleSheet("padding: 15px; background: #ecf0f1; border-radius: 4px; color: #7f8c8d; font-style: italic; font-size: 12px;")
            self.migration_filter_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.migration_filter_layout.addWidget(self.migration_filter_placeholder)
            self.migration_filter_info.setVisible(False)
            return
        
        # Collect all unique source types from all models
        all_source_types = set()
        for model in self.migration_models_data:
            for source in model['sources']:
                all_source_types.add(source['source_type'])
        
        if not all_source_types:
            no_sources_label = QLabel("⚠️ No data sources detected in scanned models")
            no_sources_label.setStyleSheet("padding: 15px; background: #ffe6e6; border-radius: 4px; color: #c0392b; font-size: 12px;")
            no_sources_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.migration_filter_layout.addWidget(no_sources_label)
            self.migration_filter_info.setVisible(False)
            return
        
        # Create filter checkboxes dynamically
        self.migration_filter_checkboxes = {}
        
        # Add "ALL" option first
        all_checkbox = QCheckBox("✅ Migrate ALL data sources")
        all_checkbox.setChecked(True)
        all_checkbox.setStyleSheet("font-size: 12px; padding: 4px; font-weight: bold;")
        all_checkbox.toggled.connect(self.on_filter_changed)
        self.migration_filter_layout.addWidget(all_checkbox)
        self.migration_filter_checkboxes['ALL'] = all_checkbox
        
        # Add separator
        separator = QLabel("Or select specific source types:")
        separator.setStyleSheet("font-size: 11px; color: #7f8c8d; padding: 4px 4px 0px 4px;")
        self.migration_filter_layout.addWidget(separator)
        
        # Add checkbox for each detected source type
        source_type_names = {
            'SQL_Server': 'SQL Server',
            'Azure_SQL': 'Azure SQL',
            'Snowflake': 'Snowflake',
            'Lakehouse': 'Fabric Lakehouse',
            'Excel': 'Excel',
            'Dataverse': 'Dataverse'
        }
        
        for source_type in sorted(all_source_types):
            display_name = source_type_names.get(source_type, source_type)
            checkbox = QCheckBox(f"  • {display_name} only")
            checkbox.setStyleSheet("font-size: 12px; padding: 4px;")
            checkbox.toggled.connect(self.on_filter_changed)
            self.migration_filter_layout.addWidget(checkbox)
            self.migration_filter_checkboxes[source_type] = checkbox
        
        # Show info label
        self.migration_filter_info.setVisible(True)
        self.on_filter_changed()
    
    def select_all_models(self):
        """Select all models in the table"""
        for row in range(self.migration_models_table.rowCount()):
            checkbox_item = self.migration_models_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)
    
    def deselect_all_models(self):
        """Deselect all models in the table"""
        for row in range(self.migration_models_table.rowCount()):
            checkbox_item = self.migration_models_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
    def on_filter_changed(self):
        """Update filter info when checkboxes change"""
        if not hasattr(self, 'migration_filter_checkboxes'):
            return
        
        filters = []
        
        # Check if ALL is selected
        if 'ALL' in self.migration_filter_checkboxes and self.migration_filter_checkboxes['ALL'].isChecked():
            filters.append("ALL sources")
        else:
            # Check individual source types
            for source_type, checkbox in self.migration_filter_checkboxes.items():
                if source_type != 'ALL' and checkbox.isChecked():
                    source_type_names = {
                        'SQL_Server': 'SQL Server',
                        'Azure_SQL': 'Azure SQL',
                        'Snowflake': 'Snowflake',
                        'Lakehouse': 'Lakehouse',
                        'Excel': 'Excel',
                        'Dataverse': 'Dataverse'
                    }
                    filters.append(source_type_names.get(source_type, source_type))
        
        if not filters:
            self.migration_filter_info.setText("⚠️ No filter selected - nothing will be migrated")
            self.migration_filter_info.setStyleSheet("padding: 8px; background: #e74c3c; color: white; border-radius: 4px; font-weight: bold; font-size: 12px;")
        else:
            filter_text = ", ".join(filters)
            self.migration_filter_info.setText(f"✅ Will migrate: {filter_text}")
            self.migration_filter_info.setStyleSheet("padding: 10px; background: #d5f4e6; border-radius: 4px; color: #27ae60; font-weight: bold; font-size: 12px;")
    
    def on_target_type_changed(self, index):
        """Update target configuration inputs based on type"""
        # Clear existing inputs
        while self.migration_target_inputs_layout.count():
            item = self.migration_target_inputs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get the actual key from combo box data
        target_type = self.migration_target_combo.currentData()
        if not target_type:
            return
            
        # Get template parameters
        template = DATA_SOURCE_TEMPLATES.get(target_type, {})
        params = template.get('parameters', [])
        
        # Better label mapping
        label_mapping = {
            'server': 'Host URL',
            'database': 'Database',
            'schema': 'Schema',
            'warehouse': 'Warehouse',
            'file_path': 'File Path'
        }
        
        # Create input fields in 2-column grid layout
        self.target_input_fields = {}
        row = 0
        col = 0
        for param in params:
            label_text = label_mapping.get(param, param.replace('_', ' ').title()) + ":"
            label_widget = QLabel(label_text)
            label_widget.setFixedWidth(90)
            
            input_field = QLineEdit()
            
            # Better placeholders
            placeholder_mapping = {
                'server': 'server.database.windows.net or account.snowflakecomputing.com',
                'database': 'DatabaseName',
                'schema': 'dbo or PUBLIC',
                'warehouse': 'COMPUTE_WH',
                'file_path': 'C:\\path\\to\\file.xlsx'
            }
            input_field.setPlaceholderText(placeholder_mapping.get(param, f"Enter {param}"))
            
            # Add label and input to grid (2 columns: label-input, label-input)
            self.migration_target_inputs_layout.addWidget(label_widget, row, col * 2)
            self.migration_target_inputs_layout.addWidget(input_field, row, col * 2 + 1)
            self.target_input_fields[param] = input_field
            
            # Move to next column or next row
            col += 1
            if col >= 2:  # 2 columns
                col = 0
                row += 1
    
    def execute_bulk_migration(self):
        """Execute bulk migration across selected models with filtering"""
        import copy  # Ensure deep copy to prevent reference issues
        
        # Get selected models with DEEP COPY to prevent cross-contamination
        selected_models = []
        for row in range(self.migration_models_table.rowCount()):
            checkbox_item = self.migration_models_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                # CRITICAL: Deep copy to ensure each model has independent data
                selected_models.append(copy.deepcopy(self.migration_models_data[row]))
        
        if not selected_models:
            QMessageBox.warning(self, "Warning", "Please select at least one model")
            return
        
        # Determine filter
        filter_types = []
        if not hasattr(self, 'migration_filter_checkboxes') or not self.migration_filter_checkboxes:
            # No filters initialized, migrate all
            filter_types = None
        elif 'ALL' in self.migration_filter_checkboxes and self.migration_filter_checkboxes['ALL'].isChecked():
            filter_types = None  # Migrate all
        else:
            for source_type, checkbox in self.migration_filter_checkboxes.items():
                if source_type != 'ALL' and checkbox.isChecked():
                    filter_types.append(source_type)
        
        if filter_types is not None and len(filter_types) == 0:
            QMessageBox.warning(self, "Warning", "No source filter selected. Please select a migration strategy.")
            return
        
        # Collect target details
        target_type = self.migration_target_combo.currentData()  # Get the key, not display name
        target_details = {}
        
        for param, field in self.target_input_fields.items():
            value = field.text().strip()
            if not value:
                QMessageBox.warning(self, "Warning", f"Please fill in target parameter: {param}")
                return
            target_details[param] = value
        
        # Add schema from Rename Tables tab (if applicable for SQL Server, Snowflake, or Fabric)
        if target_type in ["SQL_Server", "Azure_SQL", "Snowflake", "Lakehouse"]:
            schema_value = self.rename_schema.text().strip() if hasattr(self, 'rename_schema') and self.rename_schema.text().strip() else 'dbo'
            target_details['schema'] = schema_value
        
        # Count sources to migrate and generate preview
        total_sources = 0
        all_previews = []
        
        for model in selected_models:
            for source in model['sources']:
                if filter_types is None or source['source_type'] in filter_types:
                    total_sources += 1
                    # Generate preview for each source
                    try:
                        preview = preview_migration(
                            source_info=source,
                            new_source_type=target_type,
                            new_connection_details=target_details,
                            dest_model_path=model['path']
                        )
                        if preview['files_to_change']:
                            all_previews.append(preview)
                    except Exception as e:
                        logging.warning(f"Preview generation failed for {model['name']}: {e}")
        
        # Show preview dialog
        if all_previews:
            # Group previews by unique model path to avoid duplicate model nodes
            models_dict = {}
            for preview in all_previews:
                model_path = preview['model_path']
                if model_path not in models_dict:
                    # First preview for this model
                    models_dict[model_path] = {
                        'model_path': model_path,
                        'model_name': preview['model_name'],
                        'source_type_from': preview['source_type_from'],
                        'source_type_to': preview['source_type_to'],
                        'files_to_change': [],
                        'summary': {
                            'total_files': 0,
                            'total_tables': 0,
                            'total_lines_changed': 0,
                            'connection_changes': preview['summary']['connection_changes']
                        }
                    }
                
                # Add files from this preview to the model's collection
                models_dict[model_path]['files_to_change'].extend(preview['files_to_change'])
                models_dict[model_path]['summary']['total_files'] += preview['summary']['total_files']
                models_dict[model_path]['summary']['total_tables'] += preview['summary']['total_tables']
                models_dict[model_path]['summary']['total_lines_changed'] += preview['summary']['total_lines_changed']
            
            # Convert dict back to list
            unique_model_previews = list(models_dict.values())
            
            # Combine all previews into single view with model boundaries preserved
            combined_preview = {
                'model_path': 'Multiple Models',
                'model_name': f"{len(unique_model_previews)} Model(s)",
                'source_type_from': all_previews[0]['source_type_from'] if all_previews else 'Multiple',
                'source_type_to': target_type,
                'files_to_change': [],
                'models_preview': unique_model_previews,  # Use grouped previews
                'summary': {
                    'total_files': 0,
                    'total_tables': 0,
                    'total_lines_changed': 0,
                    'connection_changes': target_details
                }
            }
            
            # Add all files and compute totals
            for model_preview in unique_model_previews:
                # Add model info to each file change for tracking
                for file_change in model_preview['files_to_change']:
                    file_change['model_name'] = model_preview['model_name']
                    file_change['model_path'] = model_preview['model_path']
                
                combined_preview['files_to_change'].extend(model_preview['files_to_change'])
                combined_preview['summary']['total_files'] += model_preview['summary']['total_files']
                combined_preview['summary']['total_tables'] += model_preview['summary']['total_tables']
                combined_preview['summary']['total_lines_changed'] += model_preview['summary']['total_lines_changed']
            
            # Load preview into the preview tab and switch to it
            self.load_preview_data(combined_preview)
            
            # Store migration context for later execution
            self.pending_migration_context = {
                'selected_models': selected_models,
                'filter_types': filter_types,
                'target_type': target_type,
                'target_details': target_details,
                'total_sources': total_sources
            }
            return  # Don't execute migration yet, wait for user confirmation in preview tab
        else:
            # No preview available
            QMessageBox.warning(self, "No Changes", "No changes detected for the selected models and filters.")
            return
    
    def execute_migration_from_preview(self):
        """Execute the actual migration after preview confirmation"""
        if not hasattr(self, 'pending_migration_context'):
            QMessageBox.warning(self, "Error", "No migration context available.")
            return
        
        context = self.pending_migration_context
        selected_models = context['selected_models']
        filter_types = context['filter_types']
        target_type = context['target_type']
        target_details = context['target_details']
        
        # Execute bulk migration
        self.migration_results.clear()
        self.prepend_to_text_edit(self.migration_results, "=" * 60 + "\n")
        self.prepend_to_text_edit(self.migration_results, "BULK MIGRATION STARTED")
        self.prepend_to_text_edit(self.migration_results, "=" * 60)
        
        # Switch back to migration tab to show progress
        self.tabs.setCurrentIndex(3)
        
        self.migration_progress.setVisible(True)
        self.migration_progress.setMaximum(len(selected_models))
        self.migration_progress.setValue(0)
        
        total_success = 0
        total_errors = 0
        all_errors = []
        
        for idx, model in enumerate(selected_models, 1):
            self.migration_results.append(f"\n{'='*60}")
            self.migration_results.append(f"[{idx}/{len(selected_models)}] SEMANTIC MODEL: {model['name']}")
            self.migration_results.append(f"{'='*60}")
            self.migration_results.append(f"📁 Path: {model['path']}")
            self.migration_results.append(f"📂 Folder: {Path(model['path']).name}")
            
            # CRITICAL: Log to verify this is the correct, unique model path
            tables_in_model = list((Path(model['path']) / "definition" / "tables").glob("*.tmdl")) if (Path(model['path']) / "definition" / "tables").exists() else []
            self.migration_results.append(f"📊 Tables in model: {len(tables_in_model)}")
            if tables_in_model:
                self.migration_results.append(f"    Sample tables: {', '.join([t.stem for t in tables_in_model[:5]])}...")
            
            # Filter sources
            sources_to_migrate = []
            for source in model['sources']:
                if filter_types is None or source['source_type'] in filter_types:
                    sources_to_migrate.append(source)
            
            if not sources_to_migrate:
                self.migration_results.append("  ⊘ No matching sources to migrate (skipped)")
                self.migration_progress.setValue(idx)
                continue
            
            self.migration_results.append(f"  → Found {len(sources_to_migrate)} source(s) to migrate")
            self.migration_results.append(f"  💾 Creating backup before migration...")
            
            # Create backup ONCE for the entire model before any migrations
            from utils.data_source_migration import backup_model_before_migration
            backup_success, backup_result = backup_model_before_migration(model['path'], Path(model['path']))
            if backup_success:
                self.migration_results.append(f"  ✓ Backup created: {Path(backup_result).name}")
            else:
                self.migration_results.append(f"  ⚠️ Backup warning: {backup_result} (continuing anyway)")
            
            # Process this model completely before moving to next
            model_success = 0
            model_errors = 0
            
            # Migrate each source in this model
            for source_idx, source in enumerate(sources_to_migrate, 1):
                try:
                    self.migration_results.append(f"\n  [{source_idx}/{len(sources_to_migrate)}] Migrating {source['source_type']} ({len(source['tables'])} tables)...")
                    self.migration_results.append(f"      Source Tables: {', '.join([t['name'] for t in source['tables'][:5]])}{'...' if len(source['tables']) > 5 else ''}")
                    self.migration_results.append(f"      Target Model: {Path(model['path']).name}")
                    
                    # CRITICAL: Ensure we're passing the correct model path
                    if not Path(model['path']).exists():
                        raise ValueError(f"Model path does not exist: {model['path']}")
                    
                    # CRITICAL VALIDATION: Verify source tables belong to this model
                    model_tables_path = Path(model['path']) / "definition" / "tables"
                    if model_tables_path.exists():
                        actual_tables = {f.stem for f in model_tables_path.glob("*.tmdl")}
                        source_tables = {t['name'] for t in source['tables']}
                        mismatched_tables = source_tables - actual_tables
                        
                        if mismatched_tables:
                            error_msg = f"ERROR: Source contains tables not in this model: {mismatched_tables}"
                            self.migration_results.append(f"    ⚠️ {error_msg}")
                            self.migration_results.append(f"    ⚠️ Skipping this source to prevent cross-contamination")
                            total_errors += len(mismatched_tables)
                            model_errors += len(mismatched_tables)
                            continue
                    
                    success_count, error_count, errors = migrate_all_tables(
                        source_info=source,
                        new_source_type=target_type,
                        new_connection_details=target_details,
                        dest_model_path=model['path'],  # CRITICAL: Only process tables in THIS model
                        skip_backup=True  # Backup already created once for this model
                    )
                    
                    # Check if backup warning is in errors
                    backup_warnings = [e for e in errors if 'Backup warning' in e or 'backup' in e.lower()]
                    migration_errors = [e for e in errors if e not in backup_warnings]
                    
                    if backup_warnings:
                        for warning in backup_warnings:
                            self.migration_results.append(f"    {warning}")
                    
                    total_success += success_count
                    total_errors += error_count
                    model_success += success_count
                    model_errors += error_count
                    
                    self.migration_results.append(f"    ✓ Success: {success_count} table(s)")
                    if error_count > 0:
                        self.migration_results.append(f"    ✗ Errors: {error_count}")
                        all_errors.extend(migration_errors)
                        for error in migration_errors:
                            self.migration_results.append(f"      • {error}")
                    
                except Exception as e:
                    self.migration_results.append(f"    ✗ Migration failed: {str(e)}")
                    all_errors.append(f"{model['name']}: {str(e)}")
                    total_errors += 1
                    model_errors += 1
            
            # Model summary
            self.migration_results.append(f"\n  📊 Model Summary: {model_success} success, {model_errors} errors")
            self.migration_results.append(f"  ✅ Completed: {model['name']}")
            
            self.migration_progress.setValue(idx)
            QApplication.processEvents()  # Update UI
        
        # Final summary
        self.migration_results.append("\n" + "=" * 60)
        self.migration_results.append("BULK MIGRATION COMPLETED")
        self.migration_results.append("=" * 60)
        self.migration_results.append(f"\n✓ Total Success: {total_success} table(s)")
        self.migration_results.append(f"✗ Total Errors: {total_errors}")
        self.migration_results.append(f"\n📊 Models Processed: {len(selected_models)}")
        self.migration_results.append(f"\n💾 Backups saved in: {Path(selected_models[0]['path']).parents[2] / 'BACKUP'}")
        
        self.migration_progress.setVisible(False)
        
        if total_errors == 0:
            QMessageBox.information(self, "Success",
                f"Bulk migration completed successfully!\n\n"
                f"✓ Migrated {total_success} tables across {len(selected_models)} models\n\n"
                f"💾 Backups saved in BACKUP folder\n"
                f"Use 'Publish to Fabric' to deploy changes.")
        else:
            QMessageBox.warning(self, "Completed with Errors",
                f"Bulk migration completed with some errors:\n\n"
                f"✓ Success: {total_success} tables\n"
                f"✗ Errors: {total_errors}\n\n"
                f"💾 Backups saved in BACKUP folder\n"
                f"Check results panel for details.")
    
    def execute_bulk_migration_no_preview(self):
        """Execute bulk migration WITHOUT preview (original behavior)"""
        # Get selected models
        selected_models = []
        for row in range(self.migration_models_table.rowCount()):
            checkbox_item = self.migration_models_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                selected_models.append(self.migration_models_data[row])
        
        if not selected_models:
            QMessageBox.warning(self, "Warning", "Please select at least one model")
            return
        
        # Determine filter
        filter_types = []
        if not hasattr(self, 'migration_filter_checkboxes') or not self.migration_filter_checkboxes:
            # No filters initialized, migrate all
            filter_types = None
        elif 'ALL' in self.migration_filter_checkboxes and self.migration_filter_checkboxes['ALL'].isChecked():
            filter_types = None  # Migrate all
        else:
            for source_type, checkbox in self.migration_filter_checkboxes.items():
                if source_type != 'ALL' and checkbox.isChecked():
                    filter_types.append(source_type)
        
        if filter_types is not None and len(filter_types) == 0:
            QMessageBox.warning(self, "Warning", "No source filter selected. Please select a migration strategy.")
            return
        
        # Collect target details
        target_type = self.migration_target_combo.currentData()
        target_details = {}
        
        for param, field in self.target_input_fields.items():
            value = field.text().strip()
            if not value:
                QMessageBox.warning(self, "Warning", f"Please fill in target parameter: {param}")
                return
            target_details[param] = value
        
        # Add schema from Rename Tables tab (if applicable for SQL Server, Snowflake, or Fabric)
        if target_type in ["SQL_Server", "Azure_SQL", "Snowflake", "Lakehouse"]:
            schema_value = self.rename_schema.text().strip() if hasattr(self, 'rename_schema') and self.rename_schema.text().strip() else 'dbo'
            target_details['schema'] = schema_value
        
        # Count sources to migrate
        total_sources = 0
        for model in selected_models:
            for source in model['sources']:
                if filter_types is None or source['source_type'] in filter_types:
                    total_sources += 1
        
        # Confirm
        msg = f"Bulk Migration Summary:\n\n"
        msg += f"• Models: {len(selected_models)}\n"
        msg += f"• Sources to migrate: {total_sources}\n"
        msg += f"• Target: {target_type}\n\n"
        msg += "⚠️ This will modify TMDL files directly without preview. Continue?"
        
        reply = QMessageBox.question(self, "Confirm Bulk Migration", msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Execute bulk migration
        self.migration_results.clear()
        self.prepend_to_text_edit(self.migration_results, "=" * 60 + "\n")
        self.prepend_to_text_edit(self.migration_results, "BULK MIGRATION STARTED (No Preview)")
        self.prepend_to_text_edit(self.migration_results, "=" * 60)
        
        self.migration_progress.setVisible(True)
        self.migration_progress.setMaximum(len(selected_models))
        self.migration_progress.setValue(0)
        
        total_success = 0
        total_errors = 0
        all_errors = []
        
        for idx, model in enumerate(selected_models, 1):
            self.migration_results.append(f"\n[{idx}/{len(selected_models)}] Processing: {model['name']}")
            self.migration_results.append("-" * 60)
            
            # Filter sources
            sources_to_migrate = []
            for source in model['sources']:
                if filter_types is None or source['source_type'] in filter_types:
                    sources_to_migrate.append(source)
            
            if not sources_to_migrate:
                self.migration_results.append("  ⊘ No matching sources to migrate (skipped)")
                self.migration_progress.setValue(idx)
                continue
            
            self.migration_results.append(f"  → Found {len(sources_to_migrate)} source(s) to migrate")
            self.migration_results.append(f"  💾 Creating backup before migration...")
            
            # Migrate each source in this model
            for source_idx, source in enumerate(sources_to_migrate, 1):
                try:
                    self.migration_results.append(f"\n  [{source_idx}/{len(sources_to_migrate)}] Migrating {source['source_type']} ({len(source['tables'])} tables)...")
                    
                    success_count, error_count, errors = migrate_all_tables(
                        source_info=source,
                        new_source_type=target_type,
                        new_connection_details=target_details,
                        dest_model_path=model['path']
                    )
                    
                    # Check if backup warning is in errors
                    backup_warnings = [e for e in errors if 'Backup warning' in e or 'backup' in e.lower()]
                    migration_errors = [e for e in errors if e not in backup_warnings]
                    
                    if backup_warnings:
                        for warning in backup_warnings:
                            self.migration_results.append(f"    {warning}")
                    
                    total_success += success_count
                    total_errors += error_count
                    
                    self.migration_results.append(f"    ✓ Success: {success_count} table(s)")
                    if error_count > 0:
                        self.migration_results.append(f"    ✗ Errors: {error_count}")
                        all_errors.extend(migration_errors)
                        for error in migration_errors:
                            self.migration_results.append(f"      • {error}")
                    
                except Exception as e:
                    self.migration_results.append(f"    ✗ Migration failed: {str(e)}")
                    all_errors.append(f"{model['name']}: {str(e)}")
                    total_errors += 1
            
            self.migration_progress.setValue(idx)
            QApplication.processEvents()
        
        # Final summary
        self.migration_results.append("\n" + "=" * 60)
        self.migration_results.append("BULK MIGRATION COMPLETED")
        self.migration_results.append("=" * 60)
        self.migration_results.append(f"\n✓ Total Success: {total_success} table(s)")
        self.migration_results.append(f"✗ Total Errors: {total_errors}")
        self.migration_results.append(f"\n📊 Models Processed: {len(selected_models)}")
        self.migration_results.append(f"\n💾 Backups saved in: {Path(selected_models[0]['path']).parents[2] / 'BACKUP'}")
        
        self.migration_progress.setVisible(False)
        
        if total_errors == 0:
            QMessageBox.information(self, "Success",
                f"Bulk migration completed successfully!\n\n"
                f"✓ Migrated {total_success} tables across {len(selected_models)} models\n\n"
                f"💾 Backups saved in BACKUP folder\n"
                f"Use 'Publish to Fabric' to deploy changes.")
        else:
            QMessageBox.warning(self, "Completed with Errors",
                f"Bulk migration completed with some errors:\n\n"
                f"✓ Success: {total_success} tables\n"
                f"✗ Errors: {total_errors}\n\n"
                f"💾 Backups saved in BACKUP folder\n"
                f"Check results panel for details.")
    
    def scan_rename_models(self):
        """Scan for semantic models and populate table with table counts"""
        export_path = self.export_path_input.text() or self.export_dropdown.currentText()
        if not export_path or not Path(export_path).exists():
            QMessageBox.warning(self, "Warning", "Please index an export first in Assessment tab")
            return
        
        self.rename_models_table.setRowCount(0)
        self.rename_models_data = []
        
        # Scan for .SemanticModel folders (exclude BACKUP folders)
        models = []
        for item in Path(export_path).rglob("*.SemanticModel"):
            # Skip if path contains BACKUP folder
            if "BACKUP" in str(item).upper():
                continue
            if item.is_dir() and (item / "definition").exists():
                models.append(item)
        
        if not models:
            QMessageBox.information(self, "Info", "No semantic models found in current export")
            return
        
        # Populate table with models and detect tables
        for model_path in models:
            try:
                tables = get_tables_from_model(str(model_path))
                table_count = len(tables)
                workspace_name = model_path.parent.name if model_path.parent.name else "Unknown"
                
                # Store model data
                self.rename_models_data.append({
                    'path': str(model_path),
                    'name': model_path.name,
                    'workspace': workspace_name,
                    'tables': tables,
                    'table_count': table_count
                })
                
                # Add to table
                row = self.rename_models_table.rowCount()
                self.rename_models_table.insertRow(row)
                
                # Checkbox
                checkbox_item = QTableWidgetItem()
                checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
                self.rename_models_table.setItem(row, 0, checkbox_item)
                
                # Workspace name
                workspace_item = QTableWidgetItem(workspace_name)
                self.rename_models_table.setItem(row, 1, workspace_item)
                
                # Model name
                name_item = QTableWidgetItem(model_path.name)
                name_item.setToolTip(str(model_path))
                self.rename_models_table.setItem(row, 2, name_item)
                
                # Table count
                table_item = QTableWidgetItem(str(table_count))
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.rename_models_table.setItem(row, 3, table_item)
                
            except Exception as e:
                print(f"Error processing {model_path}: {e}")
        
        self.rename_models_table.resizeColumnsToContents()
        self.statusBar().showMessage(f"Found {len(self.rename_models_data)} semantic model(s)")
    
    def load_tables_from_selected_models(self):
        """Load all tables from selected models and populate preview table"""
        # Get selected models
        selected_models = []
        for row in range(self.rename_models_table.rowCount()):
            checkbox_item = self.rename_models_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                selected_models.append(self.rename_models_data[row])
        
        if not selected_models:
            QMessageBox.warning(self, "Warning", "Please select at least one model")
            return
        
        # Clear existing table
        self.rename_table_preview.setRowCount(0)
        self.rename_table_data = []  # Store for later use
        
        # Populate table with all tables from all selected models
        # Get default schema value from the field (only used for New Schema default, NOT for Current Schema)
        default_schema = self.rename_schema.text().strip() if hasattr(self, 'rename_schema') and self.rename_schema.text().strip() else 'dbo'
        
        for model in selected_models:
            # Extract workspace name from path (e.g., "WorkspaceName/Model.SemanticModel")
            workspace_name = Path(model['path']).parent.name if Path(model['path']).parent.name else "Unknown"
            
            for table in model['tables']:
                row = self.rename_table_preview.rowCount()
                self.rename_table_preview.insertRow(row)
                
                # Current Schema: ONLY from table file, no fallback (static value from source)
                current_schema = table.get('schema', None)  # None if not found in file
                current_schema_display = current_schema if current_schema else ""
                
                # New Schema: Use current schema if available, otherwise use default from textbox
                new_schema = current_schema if current_schema else default_schema
                
                # Store data
                self.rename_table_data.append({
                    'model_path': model['path'],
                    'model_name': model['name'],
                    'workspace_name': workspace_name,
                    'table_name': table['name'],
                    'schema': current_schema,  # Store actual schema from file (can be None)
                    'column_count': table['column_count']
                })
                
                # Workspace name (read-only)
                workspace_item = QTableWidgetItem(workspace_name)
                workspace_item.setFlags(workspace_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.rename_table_preview.setItem(row, 0, workspace_item)
                
                # Model name (read-only)
                model_item = QTableWidgetItem(model['name'])
                model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model_item.setToolTip(model['path'])
                self.rename_table_preview.setItem(row, 1, model_item)
                
                # Current Schema (read-only) - ONLY from actual table file, never changes
                current_schema_item = QTableWidgetItem(current_schema_display)
                current_schema_item.setFlags(current_schema_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                current_schema_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.rename_table_preview.setItem(row, 2, current_schema_item)
                
                # Current name (read-only)
                current_item = QTableWidgetItem(table['name'])
                current_item.setFlags(current_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.rename_table_preview.setItem(row, 3, current_item)
                
                # New Schema (editable) - uses current schema if found, otherwise default from textbox
                new_schema_item = QTableWidgetItem(new_schema)
                new_schema_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.rename_table_preview.setItem(row, 4, new_schema_item)
                
                # New name (editable) - default to current name
                new_item = QTableWidgetItem(table['name'])
                self.rename_table_preview.setItem(row, 5, new_item)
                
                # Column count (read-only)
                col_count_item = QTableWidgetItem(str(table['column_count']))
                col_count_item.setFlags(col_count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                col_count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.rename_table_preview.setItem(row, 6, col_count_item)
        
        self.rename_table_preview.resizeColumnsToContents()
        total_tables = self.rename_table_preview.rowCount()
        self.statusBar().showMessage(f"Loaded {total_tables} table(s) from {len(selected_models)} model(s)")
        QMessageBox.information(self, "Tables Loaded", 
            f"Loaded {total_tables} tables from {len(selected_models)} model(s).\n\n"
            f"You can now:\n"
            f"• Apply prefix/suffix to all tables\n"
            f"• Edit individual table names in 'New Name' column\n"
            f"• Click 'Execute Bulk Rename' when ready")
    
    def apply_prefix_suffix_to_tables(self):
        """Apply prefix/suffix/case transformation to all tables in the preview"""
        if self.rename_table_preview.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "Please load tables first")
            return
        
        prefix = self.rename_prefix.text().strip()
        suffix = self.rename_suffix.text().strip()
        transformation = self.rename_transformation.currentText().split()[0] if self.rename_transformation.currentText() != "None" else None
        schema = self.rename_schema.text().strip() if hasattr(self, 'rename_schema') else 'dbo'
        
        if not prefix and not suffix and not transformation:
            QMessageBox.warning(self, "Warning", "Please provide at least a prefix, suffix, or case transformation")
            return
        
        # Apply to all rows
        for row in range(self.rename_table_preview.rowCount()):
            # Update New Schema column with schema field value
            new_schema_item = QTableWidgetItem(schema)
            new_schema_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rename_table_preview.setItem(row, 4, new_schema_item)  # New Schema is column 4
            
            current_name_item = self.rename_table_preview.item(row, 3)  # Current Name is now column 3
            if current_name_item:
                current_name = current_name_item.text()
                
                # Apply case transformation first if selected
                new_name = current_name
                if transformation:
                    new_name = apply_column_transformation(new_name, transformation)
                
                # Then apply prefix/suffix
                new_name = f"{prefix}{new_name}{suffix}"
                
                self.rename_table_preview.setItem(row, 5, QTableWidgetItem(new_name))  # New Name is now column 5
        
        msg_parts = []
        if prefix:
            msg_parts.append(f"prefix '{prefix}'")
        if suffix:
            msg_parts.append(f"suffix '{suffix}'")
        if transformation:
            msg_parts.append(f"transformation '{transformation}'")
        
        self.statusBar().showMessage(f"Applied {', '.join(msg_parts)} to {self.rename_table_preview.rowCount()} tables")
    
    def select_all_rename_models(self):
        """Select all models in the rename table"""
        for row in range(self.rename_models_table.rowCount()):
            checkbox_item = self.rename_models_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)
    
    def deselect_all_rename_models(self):
        """Deselect all models in the rename table"""
        for row in range(self.rename_models_table.rowCount()):
            checkbox_item = self.rename_models_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
    def load_rename_tables(self):
        """Load tables from selected model"""
        model_path = self.rename_model_combo.currentText()
        if not model_path:
            return
        
        try:
            self.rename_tables_data = get_tables_from_model(model_path)
            self.populate_rename_table()
            self.statusBar().showMessage(f"Loaded {len(self.rename_tables_data)} table(s)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tables:\n{str(e)}")
    
    def populate_rename_table(self):
        """Populate the rename table widget"""
        self.rename_table_widget.setRowCount(len(self.rename_tables_data))
        
        for i, table in enumerate(self.rename_tables_data):
            # Current name (read-only)
            current_item = QTableWidgetItem(table['name'])
            current_item.setFlags(current_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.rename_table_widget.setItem(i, 0, current_item)
            
            # New name (editable)
            prefix = self.rename_prefix.text()
            suffix = self.rename_suffix.text()
            new_name = f"{prefix}{table['name']}{suffix}"
            new_item = QTableWidgetItem(new_name)
            self.rename_table_widget.setItem(i, 1, new_item)
            
            # Column count (read-only)
            col_count_item = QTableWidgetItem(str(table['column_count']))
            col_count_item.setFlags(col_count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.rename_table_widget.setItem(i, 2, col_count_item)
        
        self.rename_table_widget.resizeColumnsToContents()
    
    def apply_prefix_suffix(self):
        """Apply prefix/suffix to all table names"""
        if not self.rename_tables_data:
            return
        
        prefix = self.rename_prefix.text()
        suffix = self.rename_suffix.text()
        
        for i, table in enumerate(self.rename_tables_data):
            new_name = f"{prefix}{table['name']}{suffix}"
            self.rename_table_widget.setItem(i, 1, QTableWidgetItem(new_name))
    
    def execute_bulk_rename(self):
        """Execute bulk rename using the table preview mappings"""
        if self.rename_table_preview.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "Please load tables first")
            return
        
        # Build rename mappings grouped by model
        # Structure: {model_path: {old_name: {'new_name': str, 'old_schema': str, 'new_schema': str}}}
        model_mappings = {}
        changes_count = 0
        
        for row in range(self.rename_table_preview.rowCount()):
            table_data = self.rename_table_data[row]
            model_path = table_data['model_path']
            old_name = table_data['table_name']
            old_schema = table_data.get('schema') or 'dbo'  # Use 'dbo' if None (from file)
            
            new_name_item = self.rename_table_preview.item(row, 5)  # New Name is column 5
            new_name = new_name_item.text() if new_name_item else old_name
            
            new_schema_item = self.rename_table_preview.item(row, 4)  # New Schema is column 4
            new_schema = new_schema_item.text().strip() if (new_schema_item and new_schema_item.text().strip()) else old_schema
            
            # Check if there's any change (name or schema)
            if old_name != new_name or old_schema != new_schema:
                if model_path not in model_mappings:
                    model_mappings[model_path] = {}
                model_mappings[model_path][old_name] = {
                    'new_name': new_name,
                    'old_schema': old_schema,
                    'new_schema': new_schema
                }
                changes_count += 1
        
        if changes_count == 0:
            QMessageBox.information(self, "Info", "No tables to rename (all names are unchanged)")
            return
        
        # Confirm
        msg = f"Bulk Rename Summary:\n\n"
        msg += f"• Models affected: {len(model_mappings)}\n"
        msg += f"• Total tables to rename: {changes_count}\n\n"
        msg += "This will update table names and all references (DAX, M queries, relationships).\n\n"
        msg += "Continue?"
        
        reply = QMessageBox.question(self, "Confirm Bulk Rename", msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Execute bulk rename
        self.rename_results.clear()
        self.rename_results.append("=" * 60)
        self.rename_results.append("BULK RENAME STARTED")
        self.rename_results.append("=" * 60 + "\n")
        
        self.rename_progress.setVisible(True)
        self.rename_progress.setMaximum(len(model_mappings))
        self.rename_progress.setValue(0)
        
        total_success = 0
        total_errors = 0
        all_errors = []
        
        for idx, (model_path, rename_mapping) in enumerate(model_mappings.items(), 1):
            # Find model name
            model_name = Path(model_path).name
            
            self.rename_results.append(f"\n[{idx}/{len(model_mappings)}] Processing: {model_name}")
            self.rename_results.append("-" * 60)
            self.rename_results.append(f"  → Renaming {len(rename_mapping)} table(s)...")
            
            try:
                # Get checkbox value for backend renaming
                rename_backend = self.rename_backend_table.isChecked()
                print(f"DEBUG: rename_backend checkbox state = {rename_backend}")
                self.rename_results.append(f"  → Backend rename: {'ENABLED' if rename_backend else 'DISABLED (display name only)'}")
                
                success_count, error_count, errors = rename_tables_bulk(model_path, rename_mapping, rename_backend, with_schema=True)
                
                total_success += success_count
                total_errors += error_count
                
                self.rename_results.append(f"    ✓ Success: {success_count} table(s)")
                if error_count > 0:
                    self.rename_results.append(f"    ✗ Errors: {error_count}")
                    all_errors.extend(errors)
                    for error in errors:
                        self.rename_results.append(f"      • {error}")
                
            except Exception as e:
                self.rename_results.append(f"    ✗ Rename failed: {str(e)}")
                all_errors.append(f"{model_name}: {str(e)}")
                total_errors += 1
            
            self.rename_progress.setValue(idx)
            QApplication.processEvents()  # Update UI
        
        # Final summary
        self.rename_results.append("\n" + "=" * 60)
        self.rename_results.append("BULK RENAME COMPLETED")
        self.rename_results.append("=" * 60)
        self.rename_results.append(f"\n✓ Total Success: {total_success} table(s)")
        self.rename_results.append(f"✗ Total Errors: {total_errors}")
        self.rename_results.append(f"\n📊 Models Processed: {len(model_mappings)}")
        
        self.rename_progress.setVisible(False)
        
        # Reload the table list to reflect the new names
        if total_success > 0:
            self.rename_results.append("\n🔄 Refreshing table list with updated names...")
            try:
                # Store current selections
                current_workspace = self.rename_workspace_combo.currentText()
                current_dataset = self.rename_dataset_combo.currentText()
                
                # Reload tables for the current model
                if current_dataset and current_dataset != "All Datasets":
                    # Reload tables for this specific model
                    workspace_path = self.rename_base_path / current_workspace
                    model_path = workspace_path / f"{current_dataset}.SemanticModel"
                    
                    if model_path.exists():
                        self.rename_tables_data = get_tables_from_model(str(model_path))
                        self.populate_rename_table_widget()
                        self.rename_results.append("   ✓ Table list refreshed successfully")
                else:
                    self.rename_results.append("   ℹ️ Please reload the specific dataset to see updated names")
            except Exception as e:
                self.rename_results.append(f"   ⚠️ Could not auto-refresh table list: {str(e)}")
        
        if total_errors == 0:
            QMessageBox.information(self, "Success",
                f"Bulk rename completed successfully!\n\n"
                f"✓ Renamed {total_success} tables across {len(model_mappings)} models\n\n"
                f"Use 'Publish to Fabric' to deploy changes.")
        else:
            QMessageBox.warning(self, "Completed with Errors",
                f"Bulk rename completed with some errors:\n\n"
                f"✓ Success: {total_success} tables\n"
                f"✗ Errors: {total_errors}\n\n"
                f"Check results panel for details.")
    
    # ============ Column Rename Methods ============
    
    def scan_column_models(self):
        """Scan for semantic models and populate filters"""
        export_path = self.export_path_input.text() or self.export_dropdown.currentText()
        if not export_path or not Path(export_path).exists():
            QMessageBox.warning(self, "Warning", "Please index an export first in Assessment tab")
            return
        
        self.column_models_data = []
        workspaces = set()
        models = []
        
        # Scan for .SemanticModel folders
        for item in Path(export_path).rglob("*.SemanticModel"):
            if "BACKUP" in str(item).upper():
                continue
            if item.is_dir() and (item / "definition").exists():
                workspace_name = item.parent.name if item.parent.name else "Unknown"
                workspaces.add(workspace_name)
                
                # Get tables for this model
                tables = get_tables_from_model(str(item))
                
                self.column_models_data.append({
                    'path': str(item),
                    'name': item.name,
                    'workspace': workspace_name,
                    'tables': tables
                })
        
        if not self.column_models_data:
            QMessageBox.information(self, "Info", "No semantic models found")
            return
        
        # Populate workspace filter
        self.col_workspace_filter.blockSignals(True)
        self.col_workspace_filter.clear()
        self.col_workspace_filter.addItem("All Workspaces")
        self.col_workspace_filter.addItems(sorted(workspaces))
        self.col_workspace_filter.setCurrentIndex(0)  # Set to "All Workspaces"
        self.col_workspace_filter.blockSignals(False)
        
        # Initialize model and table filters
        self.filter_column_tables()
        
        self.statusBar().showMessage(f"Found {len(self.column_models_data)} models in {len(workspaces)} workspaces")
    
    def filter_column_tables(self):
        """Filter models and tables based on workspace and model selection"""
        if not hasattr(self, 'column_models_data') or not self.column_models_data:
            return
            
        workspace = self.col_workspace_filter.currentText()
        model = self.col_model_filter.currentText()
        
        # Get sender to determine which dropdown triggered the call
        sender = self.sender()
        
        # If workspace changed, update model dropdown
        if sender == self.col_workspace_filter or not model:
            # Filter models by workspace
            filtered_models = self.column_models_data
            if workspace and workspace != "All Workspaces":
                filtered_models = [m for m in self.column_models_data if m['workspace'] == workspace]
            
            # Populate model filter
            self.col_model_filter.blockSignals(True)
            self.col_model_filter.clear()
            self.col_model_filter.addItem("All Models")
            model_names = sorted(set(m['name'] for m in filtered_models))
            self.col_model_filter.addItems(model_names)
            self.col_model_filter.blockSignals(False)
            
            # Reset model selection
            model = "All Models"
        
        # Filter models by workspace and model selection
        filtered_models = self.column_models_data
        if workspace and workspace != "All Workspaces":
            filtered_models = [m for m in filtered_models if m['workspace'] == workspace]
        if model and model != "All Models":
            filtered_models = [m for m in filtered_models if m['name'] == model]
        
        # Populate table filter
        self.col_table_filter.blockSignals(True)
        self.col_table_filter.clear()
        self.col_table_filter.addItem("All Tables")
        
        all_tables = set()
        for model_data in filtered_models:
            for table in model_data['tables']:
                all_tables.add(table['name'])
        
        self.col_table_filter.addItems(sorted(all_tables))
        self.col_table_filter.blockSignals(False)
    
    def load_columns_for_selected_table(self):
        """Load columns based on current filter selection"""
        workspace = self.col_workspace_filter.currentText()
        model = self.col_model_filter.currentText()
        table = self.col_table_filter.currentText()
        
        if not self.column_models_data:
            QMessageBox.warning(self, "Warning", "Please scan models first")
            return
        
        # Filter models
        filtered_models = self.column_models_data
        if workspace != "All Workspaces":
            filtered_models = [m for m in filtered_models if m['workspace'] == workspace]
        if model != "All Models":
            filtered_models = [m for m in filtered_models if m['name'] == model]
        
        # Clear table
        self.column_preview_table.setRowCount(0)
        self.column_data = []
        
        # Load columns
        for model_data in filtered_models:
            for table_info in model_data['tables']:
                # Apply table filter
                if table != "All Tables" and table_info['name'] != table:
                    continue
                
                # Get columns from table file
                columns = get_columns_from_table(table_info['file_path'])
                logging.info(f"Loading {len(columns)} columns from table {table_info['name']}")
                
                for col in columns:
                    logging.debug(f"Adding column {col['name']} to table")
                    row = self.column_preview_table.rowCount()
                    self.column_preview_table.insertRow(row)
                    
                    # Store data
                    self.column_data.append({
                        'model_path': model_data['path'],
                        'model_name': model_data['name'],
                        'workspace_name': model_data['workspace'],
                        'table_name': table_info['name'],
                        'column_name': col['name'],
                        'column_type': col['type'],
                        'is_calculated': col.get('is_calculated', False)
                    })
                    
                    # Workspace (read-only)
                    workspace_item = QTableWidgetItem(model_data['workspace'])
                    workspace_item.setFlags(workspace_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.column_preview_table.setItem(row, 0, workspace_item)
                    
                    # Model (read-only)
                    model_item = QTableWidgetItem(model_data['name'])
                    model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.column_preview_table.setItem(row, 1, model_item)
                    
                    # Table (read-only)
                    table_item = QTableWidgetItem(table_info['name'])
                    table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.column_preview_table.setItem(row, 2, table_item)
                    
                    # Current name (read-only)
                    current_item = QTableWidgetItem(col['name'])
                    current_item.setFlags(current_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.column_preview_table.setItem(row, 3, current_item)
                    
                    # New name (editable) - default to current name
                    new_item = QTableWidgetItem(col['name'])
                    self.column_preview_table.setItem(row, 4, new_item)
                    
                    # Type (read-only)
                    type_item = QTableWidgetItem(col['type'])
                    type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.column_preview_table.setItem(row, 5, type_item)
                    
                    # Calculated (read-only)
                    calc_item = QTableWidgetItem("Yes" if col.get('is_calculated', False) else "No")
                    calc_item.setFlags(calc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    calc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.column_preview_table.setItem(row, 6, calc_item)
        
        self.column_preview_table.resizeColumnsToContents()
        total_columns = self.column_preview_table.rowCount()
        self.statusBar().showMessage(f"Loaded {total_columns} column(s)")
        
        if total_columns == 0:
            QMessageBox.information(self, "Info", "No columns found matching the current filters")
    
    def apply_column_transformation(self):
        """Apply transformation to columns in preview table"""
        if self.column_preview_table.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "Please load columns first")
            return
        
        prefix = self.col_prefix.text().strip()
        suffix = self.col_suffix.text().strip()
        transformation_text = self.col_transformation.currentText()
        transformation = transformation_text.split()[0] if transformation_text != "None" else ""
        
        if not prefix and not suffix and transformation == "":
            QMessageBox.warning(self, "Warning", "Please select a transformation or enter prefix/suffix")
            return
        
        # Apply to all rows
        for row in range(self.column_preview_table.rowCount()):
            current_name_item = self.column_preview_table.item(row, 3)
            if current_name_item:
                current_name = current_name_item.text()
                new_name = apply_column_transformation(current_name, transformation, prefix, suffix)
                self.column_preview_table.setItem(row, 4, QTableWidgetItem(new_name))
        
        self.statusBar().showMessage(f"Applied transformation to {self.column_preview_table.rowCount()} columns")
    
    def execute_column_rename(self):
        """Execute column rename using the preview table mappings"""
        if self.column_preview_table.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "Please load columns first")
            return
        
        # Build rename mappings grouped by model and table
        # Structure: {model_path: {table_name: {old_col: new_col}}}
        model_mappings = {}
        changes_count = 0
        
        for row in range(self.column_preview_table.rowCount()):
            col_data = self.column_data[row]
            model_path = col_data['model_path']
            table_name = col_data['table_name']
            old_col = col_data['column_name']
            
            new_name_item = self.column_preview_table.item(row, 4)
            new_col = new_name_item.text() if new_name_item else old_col
            
            if old_col != new_col:
                if model_path not in model_mappings:
                    model_mappings[model_path] = {}
                if table_name not in model_mappings[model_path]:
                    model_mappings[model_path][table_name] = {}
                model_mappings[model_path][table_name][old_col] = new_col
                changes_count += 1
        
        if changes_count == 0:
            QMessageBox.information(self, "Info", "No columns to rename (all names are unchanged)")
            return
        
        # Get checkbox values
        rename_source_column = self.col_rename_source.isChecked()
        update_visuals = self.col_update_visuals.isChecked()
        
        # Confirm
        msg = f"Column Rename Summary:\n\n"
        msg += f"• Models affected: {len(model_mappings)}\n"
        msg += f"• Total columns to rename: {changes_count}\n"
        if rename_source_column:
            msg += f"• Will also rename sourceColumn (backend column)\n"
        else:
            msg += f"• Will keep sourceColumn unchanged (display name only)\n"
        if update_visuals:
            msg += f"• Will update report visual references (Entity, Property, queryRef, nativeQueryRef)\n"
        else:
            msg += f"• Will skip report visual updates\n"
        msg += "\nThis will update column names and all references (DAX, M queries, relationships).\n\n"
        msg += "Continue?"
        
        reply = QMessageBox.question(self, "Confirm Column Rename", msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Execute rename
        self.col_rename_results.clear()
        self.col_rename_results.append("=" * 60)
        self.col_rename_results.append("COLUMN RENAME STARTED")
        self.col_rename_results.append("=" * 60)
        if rename_source_column:
            self.col_rename_results.append("⚠️ Mode: Display name AND sourceColumn (backend column)")
        else:
            self.col_rename_results.append("ℹ️ Mode: Display name only (sourceColumn unchanged)")
        if update_visuals:
            self.col_rename_results.append("📊 Updating report visual references")
        else:
            self.col_rename_results.append("📊 Skipping report visual updates")
        self.col_rename_results.append("")
        
        self.col_rename_progress.setVisible(True)
        self.col_rename_progress.setMaximum(len(model_mappings))
        self.col_rename_progress.setValue(0)
        
        total_success = 0
        total_errors = 0
        all_errors = []
        
        for idx, (model_path, table_mappings) in enumerate(model_mappings.items(), 1):
            model_name = Path(model_path).name
            
            self.col_rename_results.append(f"\n[{idx}/{len(model_mappings)}] Processing: {model_name}")
            self.col_rename_results.append("-" * 60)
            
            total_cols = sum(len(cols) for cols in table_mappings.values())
            self.col_rename_results.append(f"  → Renaming {total_cols} column(s) across {len(table_mappings)} table(s)...")
            
            try:
                success_count, error_count, errors = rename_columns_bulk(model_path, table_mappings, rename_source_column, update_visuals)
                
                total_success += success_count
                total_errors += error_count
                
                self.col_rename_results.append(f"    ✓ Success: {success_count} column(s)")
                if error_count > 0:
                    self.col_rename_results.append(f"    ✗ Errors: {error_count}")
                    all_errors.extend(errors)
                    for error in errors:
                        self.col_rename_results.append(f"      • {error}")
                
            except Exception as e:
                self.col_rename_results.append(f"    ✗ Rename failed: {str(e)}")
                all_errors.append(f"{model_name}: {str(e)}")
                total_errors += 1
            
            self.col_rename_progress.setValue(idx)
            QApplication.processEvents()
        
        # Final summary
        self.col_rename_results.append("\n" + "=" * 60)
        self.col_rename_results.append("COLUMN RENAME COMPLETED")
        self.col_rename_results.append("=" * 60)
        self.col_rename_results.append(f"\n✓ Total Success: {total_success} column(s)")
        self.col_rename_results.append(f"✗ Total Errors: {total_errors}")
        self.col_rename_results.append(f"\n📊 Models Processed: {len(model_mappings)}")
        
        self.col_rename_progress.setVisible(False)
        
        if total_errors == 0:
            QMessageBox.information(self, "Success",
                f"Column rename completed successfully!\n\n"
                f"✓ Renamed {total_success} columns across {len(model_mappings)} models\n\n"
                f"Use 'Upload to Fabric' tab to deploy changes.")
        else:
            QMessageBox.warning(self, "Completed with Errors",
                f"Column rename completed with some errors:\n\n"
                f"✓ Success: {total_success} columns\n"
                f"✗ Errors: {total_errors}\n\n"
                f"Check results panel for details.")
    
    def check_fabric_auth(self):
        """Check if Fabric client credentials are configured (Python-based, no PowerShell)"""
        try:
            # Check if config.md exists with credentials
            config_path = self.app_data_dir / "config.md"
            
            if not config_path.exists():
                self.auth_status_label.setText("Config not found")
                self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.warning(self, "Configuration Missing",
                    "Configuration file not found.\n\n"
                    "Please configure your Azure credentials in the Configuration tab.")
                return
            
            # Read and validate config
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            import re
            tenant_match = re.search(r'tenantId\s*=\s*"([^"]+)"', config_content)
            client_match = re.search(r'clientId\s*=\s*"([^"]+)"', config_content)
            secret_match = re.search(r'clientSecret\s*=\s*"([^"]+)"', config_content)
            
            if not (tenant_match and client_match and secret_match):
                self.auth_status_label.setText("Invalid config")
                self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.warning(self, "Invalid Configuration",
                    "Configuration file is incomplete.\n\n"
                    "Please ensure all credentials are filled in the Configuration tab.")
                return
            
            # Test authentication with Azure
            try:
                from services.fabric_client import FabricClient, FabricConfig
                
                config = FabricConfig(
                    tenant_id=tenant_match.group(1),
                    client_id=client_match.group(1),
                    client_secret=secret_match.group(1)
                )
                
                client = FabricClient(config)
                client.authenticate()
                
                self.auth_status_label.setText("Authenticated ✓")
                self.auth_status_label.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(self, "Success", 
                    "Azure authentication successful!\n\n"
                    "You can now use the Download and Upload features.")
            except Exception as auth_error:
                self.auth_status_label.setText("Auth failed")
                self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.critical(self, "Authentication Failed",
                    f"Failed to authenticate with Azure:\n\n{str(auth_error)}\n\n"
                    "Please verify your credentials in the Configuration tab.")
                
        except Exception as e:
            self.auth_status_label.setText("Error")
            self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Failed to check authentication:\n{str(e)}")
    
    def scan_publish_models(self):
        """Scan for semantic models to publish"""
        export_path = self.export_path_input.text() or self.export_dropdown.currentText()
        if not export_path or not Path(export_path).exists():
            QMessageBox.warning(self, "Warning", "Please index an export first in Assessment tab")
            return
        
        self.publish_model_combo.clear()
        models = []
        
        # Scan for .SemanticModel folders (exclude BACKUP folders)
        for item in Path(export_path).rglob("*.SemanticModel"):
            # Skip if path contains BACKUP folder
            if "BACKUP" in str(item).upper():
                continue
            if item.is_dir() and (item / "definition").exists():
                models.append(str(item))
        
        # Scan for .Report folders (exclude BACKUP folders)
        for item in Path(export_path).rglob("*.Report"):
            # Skip if path contains BACKUP folder
            if "BACKUP" in str(item).upper():
                continue
            if item.is_dir() and (item / "definition.pbir").exists():
                models.append(str(item))
        
        if models:
            self.publish_model_combo.addItems(models)
            self.statusBar().showMessage(f"Found {len(models)} item(s) to publish")
        else:
            QMessageBox.information(self, "Info", "No items found to publish")
    
    def load_publish_items(self):
        """Load items from selected model path"""
        model_path = self.publish_model_combo.currentText()
        if not model_path:
            return
        
        # Clear existing checkboxes
        for checkbox in self.publish_checkboxes:
            checkbox.deleteLater()
        self.publish_checkboxes.clear()
        
        # Find all .SemanticModel and .Report items in the parent directory
        model_parent = Path(model_path).parent
        items = []
        
        for item in model_parent.iterdir():
            if item.is_dir() and (item.suffix == ".SemanticModel" or item.suffix == ".Report"):
                items.append(item)
        
        # Create checkboxes for each item
        for item in sorted(items, key=lambda x: x.name):
            item_type = item.suffix[1:]  # Remove the dot
            checkbox = QCheckBox(f"{item.name} ({item_type})")
            checkbox.setChecked(True)
            checkbox.setProperty("item_path", str(item))
            checkbox.setProperty("item_name", item.name)
            checkbox.setProperty("item_type", item_type)
            self.publish_checkboxes.append(checkbox)
            self.publish_items_layout.addWidget(checkbox)
        
        if items:
            self.statusBar().showMessage(f"Loaded {len(items)} item(s) for publishing")
        else:
            info_label = QLabel("No items found in this location")
            info_label.setStyleSheet("color: gray; font-style: italic;")
            self.publish_items_layout.addWidget(info_label)
    
    def execute_publish(self):
        """Execute Fabric publish using Python REST API"""
        workspace_name = self.publish_workspace_input.text().strip()
        if not workspace_name:
            QMessageBox.warning(self, "Warning", "Please enter a target workspace name")
            return
        
        # Collect selected items and sort by type (SemanticModel first, then Report)
        selected_items = []
        for checkbox in self.publish_checkboxes:
            if checkbox.isChecked():
                item_path = checkbox.property("item_path")
                item_name = checkbox.property("item_name")
                item_type = checkbox.property("item_type")
                selected_items.append({
                    "name": item_name,
                    "path": item_path,
                    "type": item_type
                })
        
        # Sort: SemanticModel first (priority 0), then Reports (priority 1), others (priority 2)
        def get_priority(item):
            item_type = item.get("type", "").lower()
            if "semanticmodel" in item_type or "dataset" in item_type:
                return 0
            elif "report" in item_type:
                return 1
            else:
                return 2
        
        selected_items.sort(key=get_priority)
        
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select at least one item to publish")
            return
        
        # Confirm
        msg = f"Publish {len(selected_items)} item(s) to workspace '{workspace_name}'?\n\n"
        msg += "Items:\n"
        for item in selected_items:
            msg += f"  • {item['name']}\n"
        msg += "\nThis will:\n"
        msg += "• Authenticate using config.md credentials\n"
        msg += "• Upload items to Fabric workspace\n"
        msg += "• Overwrite existing items with same names\n\n"
        msg += "Continue?"
        
        reply = QMessageBox.question(self, "Confirm Publish", msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Clear results
        self.publish_results.clear()
        self.publish_results.append("Starting publish operation...\n")
        self.publish_results.append(f"Workspace: {workspace_name}\n")
        self.publish_results.append(f"Items: {len(selected_items)}\n")
        self.publish_results.append(f"Order: SemanticModels first, then Reports\n\n")
        QApplication.processEvents()
        
        # Show progress bar
        self.publish_progress_bar.setVisible(True)
        self.publish_progress_bar.setRange(0, len(selected_items))
        self.publish_progress_bar.setValue(0)
        
        # Load configuration
        config_file = self.app_data_dir / "config.md"
        if not config_file.exists():
            QMessageBox.critical(self, "Error",
                "config.md not found. Please configure credentials in Configuration tab.")
            self.publish_progress_bar.setVisible(False)
            return
        
        try:
            config = load_config_from_file(config_file)
            self.publish_results.append("✓ Configuration loaded\n")
            QApplication.processEvents()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid configuration:\n{str(e)}")
            self.publish_progress_bar.setVisible(False)
            return
        
        # Disable publish button during execution
        self.publish_btn.setEnabled(False)
        
        # Run upload in separate thread
        def run_upload():
            try:
                # Create client and authenticate
                client = FabricClient(config)
                client.authenticate()
                
                # Get workspace ID by name
                workspaces = client.list_workspaces()
                target_ws = None
                for ws in workspaces:
                    if ws.get("displayName") == workspace_name or ws.get("name") == workspace_name:
                        target_ws = ws
                        break
                
                if not target_ws:
                    return {
                        "error": f"Workspace '{workspace_name}' not found. Please create it first in Fabric."
                    }
                
                workspace_id = target_ws["id"]
                
                # Upload each item
                results = {
                    "success_count": 0,
                    "error_count": 0,
                    "messages": []
                }
                
                for item in selected_items:
                    item_name = item["name"]
                    item_path = Path(item["path"])
                    item_type = item["type"]
                    
                    # Upload item
                    success, message = client.upload_item_definition(
                        workspace_id,
                        item_name,
                        item_type,
                        item_path
                    )
                    
                    if success:
                        results["success_count"] += 1
                    else:
                        results["error_count"] += 1
                    
                    results["messages"].append(message)
                
                return results
                
            except Exception as e:
                return {"error": str(e)}
        
        # Use QThread to run in background
        from PyQt6.QtCore import QThread
        
        class UploadThread(QThread):
            def __init__(self, func):
                super().__init__()
                self.func = func
                self.result = None
                
            def run(self):
                self.result = self.func()
        
        thread = UploadThread(run_upload)
        
        def on_finished():
            result = thread.result
            
            # Re-enable button
            self.publish_btn.setEnabled(True)
            
            # Check for errors
            if "error" in result:
                error_msg = result["error"]
                self.publish_results.append(f"\n✗ Error: {error_msg}\n")
                self.publish_progress_bar.setVisible(False)
                QMessageBox.critical(self, "Error", f"Upload failed:\n{error_msg}")
                return
            
            # Display results
            success_count = result.get("success_count", 0)
            error_count = result.get("error_count", 0)
            
            self.publish_results.append(f"\n{'='*50}\n")
            self.publish_results.append(f"✓ Upload Complete!\n")
            self.publish_results.append(f"{'='*50}\n")
            
            for message in result.get("messages", []):
                self.publish_results.append(f"{message}\n")
            
            self.publish_results.append(f"\n=== Summary ===\n")
            self.publish_results.append(f"✓ Success: {success_count}\n")
            self.publish_results.append(f"✗ Errors: {error_count}\n")
            
            # Update progress bar
            self.publish_progress_bar.setValue(success_count)
            self.publish_progress_bar.setVisible(False)
            
            # Show message
            if error_count == 0:
                QMessageBox.information(self, "Success",
                    f"Published {success_count} item(s) successfully!")
            else:
                QMessageBox.warning(self, "Completed with errors",
                    f"Success: {success_count}\n"
                    f"Errors: {error_count}\n\n"
                    f"Check the results log for details.")
        
        thread.finished.connect(on_finished)
        thread.start()
    
    def authenticate_and_list_workspaces(self):
        """Authenticate to Fabric and download all workspaces using Python REST API"""
        
        # Check prerequisites
        reply = QMessageBox.information(self, "Download Workspaces",
            "This will authenticate to Microsoft Fabric and download all workspaces.\n\n"
            "Requirements:\n"
            "✓ Valid credentials configured in Configuration tab\n"
            "✓ Network access to Microsoft Fabric\n\n"
            "This may take several minutes depending on workspace size.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if reply != QMessageBox.StandardButton.Ok:
            return
        
        try:
            self.download_progress.clear()
            self.download_progress.append("Starting authentication and download...\n")
            QApplication.processEvents()
            
            # Show progress bar
            self.download_progress_bar.setVisible(True)
            self.download_progress_bar.setRange(0, 0)  # Indeterminate progress
            
            # Check config file
            config_file = self.app_data_dir / "config.md"
            if not config_file.exists():
                QMessageBox.critical(self, "Error",
                    "config.md not found. Please create it with your Fabric credentials:\n\n"
                    "tenantId = \"your-tenant-id\"\n"
                    "clientId = \"your-client-id\"\n"
                    "clientSecret = \"your-client-secret\"")
                self.download_progress_bar.setVisible(False)
                return
            
            # Load configuration
            try:
                config = load_config_from_file(config_file)
                self.download_progress.append("✓ Configuration loaded\n")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Invalid configuration:\n{str(e)}")
                self.download_progress_bar.setVisible(False)
                return
            
            # Disable button during execution
            self.download_auth_btn.setEnabled(False)
            
            # Create downloads folder
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            export_folder = self.downloads_base / f"FabricExport_{timestamp}"
            export_folder.mkdir(parents=True, exist_ok=True)
            
            self.download_progress.append(f"Output folder: {export_folder}\n\n")
            QApplication.processEvents()
            
            # Run download in separate thread
            def run_download():
                try:
                    # Create client and authenticate
                    client = FabricClient(config)
                    client.authenticate()
                    
                    # Download all workspaces
                    def progress_callback(current, total, message):
                        # This runs in worker thread - use signals for GUI updates
                        pass
                    
                    results = client.download_all_workspaces(
                        export_folder / "Raw Files",
                        progress_callback
                    )
                    
                    return results
                    
                except Exception as e:
                    return {"error": str(e)}
            
            # Use QThread to run in background
            from PyQt6.QtCore import QThread
            
            class DownloadThread(QThread):
                def __init__(self, func):
                    super().__init__()
                    self.func = func
                    self.result = None
                    
                def run(self):
                    self.result = self.func()
            
            thread = DownloadThread(run_download)
            
            def on_finished():
                result = thread.result
                
                # Hide progress bar and re-enable button
                self.download_progress_bar.setVisible(False)
                self.download_auth_btn.setEnabled(True)
                
                # Check for errors
                if "error" in result:
                    error_msg = result["error"]
                    self.download_progress.append(f"\n✗ Error: {error_msg}\n")
                    self.download_auth_status.setText("Failed")
                    self.download_auth_status.setStyleSheet("color: red; font-weight: bold;")
                    
                    # Show helpful error message
                    if "Authentication failed" in error_msg:
                        QMessageBox.critical(self, "Authentication Error",
                            f"Failed to authenticate:\n{error_msg}\n\n"
                            "Please verify your credentials in the Configuration tab.")
                    else:
                        QMessageBox.critical(self, "Error", f"Download failed:\n{error_msg}")
                    return
                
                # Display results
                total_ws = result.get("total_workspaces", 0)
                success_count = result.get("total_items_success", 0)
                error_count = result.get("total_items_error", 0)
                
                self.download_progress.append(f"\n{'='*50}\n")
                self.download_progress.append(f"✓ Download Complete!\n")
                self.download_progress.append(f"{'='*50}\n")
                self.download_progress.append(f"Workspaces: {total_ws}\n")
                self.download_progress.append(f"Items succeeded: {success_count}\n")
                self.download_progress.append(f"Items failed: {error_count}\n")
                self.download_progress.append(f"\nSaved to: {export_folder.name}\n")
                
                # Create workspace hierarchy JSON (for compatibility)
                try:
                    workspaces_data = []
                    for ws_result in result.get("workspace_results", []):
                        workspaces_data.append({
                            "name": ws_result.get("workspace_name", "Unknown"),
                            "itemCount": ws_result.get("success_count", 0)
                        })
                    
                    hierarchy_file = export_folder / "workspaces_hierarchy.json"
                    with open(hierarchy_file, 'w', encoding='utf-8') as f:
                        json.dump({"workspaces": workspaces_data}, f, indent=2)
                    
                    self.download_workspaces_data = workspaces_data
                    
                    # Populate workspace combo
                    self.download_workspace_combo.clear()
                    for ws in workspaces_data:
                        ws_name = ws.get('name', 'Unknown')
                        item_count = ws.get('itemCount', 0)
                        self.download_workspace_combo.addItem(f"{ws_name} ({item_count} items)")
                    
                except Exception as e:
                    self.download_progress.append(f"\n⚠ Warning: Could not create hierarchy JSON: {str(e)}\n")
                
                # Create Processed_Data folder
                try:
                    from utils.folder_management import create_processed_data_folder
                    processed_data = create_processed_data_folder(export_folder)
                    self.download_progress.append(f"\n✓ Processed_Data folder created\n")
                except Exception as e:
                    self.download_progress.append(f"\n⚠ Warning: Could not create Processed_Data folder: {str(e)}\n")
                
                # Update status
                self.download_auth_status.setText("Authenticated ✓")
                self.download_auth_status.setStyleSheet("color: green; font-weight: bold;")
                
                # Show success message
                if error_count == 0:
                    QMessageBox.information(self, "Success",
                        f"Download successful!\n\n"
                        f"Workspaces: {total_ws}\n"
                        f"Items: {success_count}\n\n"
                        f"Saved to: {export_folder.name}")
                else:
                    QMessageBox.warning(self, "Completed with Errors",
                        f"Download completed with some errors:\n\n"
                        f"Workspaces: {total_ws}\n"
                        f"Items succeeded: {success_count}\n"
                        f"Items failed: {error_count}\n\n"
                        f"Check the progress log for details.")
                
                # Auto-trigger scan in Assessment tab
                try:
                    self.export_dropdown.clear()
                    self.scan_downloads_folder()
                except:
                    pass
            
            thread.finished.connect(on_finished)
            thread.start()
        
        except Exception as e:
            self.download_auth_btn.setEnabled(True)
            self.download_progress_bar.setVisible(False)
            self.download_progress.append(f"\n✗ Error: {str(e)}\n")
            QMessageBox.critical(self, "Error", f"Download failed:\n{str(e)}")
    
    def load_workspace_items(self):
        """Load items from selected workspace"""
        current_index = self.download_workspace_combo.currentIndex()
        if current_index < 0 or not self.download_workspaces_data:
            return
        
        workspace = self.download_workspaces_data[current_index]
        items = workspace.get('items', [])
        exported_items = workspace.get('exportedItems', [])
        
        # Populate table (no checkboxes, just info)
        self.download_items_table.setRowCount(len(items))
        
        for i, item in enumerate(items):
            full_name = item.get('fullName', '')
            
            # Name
            name_item = QTableWidgetItem(item.get('name', ''))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.download_items_table.setItem(i, 0, name_item)
            
            # Type
            type_item = QTableWidgetItem(item.get('type', ''))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.download_items_table.setItem(i, 1, type_item)
            
            # Status (Downloaded or Failed)
            if full_name in exported_items:
                status_item = QTableWidgetItem("✓ Downloaded")
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item = QTableWidgetItem("✗ Failed")
                status_item.setForeground(Qt.GlobalColor.red)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.download_items_table.setItem(i, 2, status_item)
        
        exported_count = len(exported_items)
        total_count = len(items)
        self.statusBar().showMessage(f"Workspace: {exported_count}/{total_count} items downloaded successfully")
    
    def toggle_download_selection(self, select_all):
        """Toggle all checkboxes in download items table"""
        for i in range(self.download_items_table.rowCount()):
            checkbox_widget = self.download_items_table.cellWidget(i, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(select_all)
    
    def execute_download(self):
        """Execute download for selected items (already downloaded, just confirm)"""
        current_index = self.download_workspace_combo.currentIndex()
        if current_index < 0 or not self.download_workspaces_data:
            QMessageBox.warning(self, "Warning", "Please authenticate and select a workspace first")
            return
        
        # Count selected items
        selected_count = 0
        for i in range(self.download_items_table.rowCount()):
            checkbox_widget = self.download_items_table.cellWidget(i, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        
        if selected_count == 0:
            QMessageBox.warning(self, "Warning", "Please select at least one item")
            return
        
        workspace = self.download_workspaces_data[current_index]
        workspace_name = workspace.get('name', 'Unknown')
        
        # Find the latest export folder
        if getattr(sys, 'frozen', False):
            app_dir = Path(sys.argv[0]).parent
        else:
            # From src/gui/main_window.py, go up 2 levels to root
            app_dir = Path(__file__).parent.parent.parent
        
        downloads_folder = app_dir / "Downloads"
        
        if downloads_folder.exists():
            export_folders = sorted(
                [f for f in downloads_folder.iterdir() if f.is_dir() and f.name.startswith("FabricExport_")],
                reverse=True
            )
            
            if export_folders:
                latest_export = export_folders[0]
                workspace_path = latest_export / "Raw Files" / workspace_name
                
                if workspace_path.exists():
                    msg = f"Items from workspace '{workspace_name}' are already downloaded to:\n\n"
                    msg += f"{workspace_path}\n\n"
                    msg += f"Total items in workspace: {len(workspace.get('items', []))}\n"
                    msg += f"Exported items: {workspace.get('exportedCount', 0)}\n"
                    msg += f"Failed items: {workspace.get('failedCount', 0)}\n\n"
                    
                    if workspace.get('failedItems'):
                        msg += "Failed items:\n"
                        for failed in workspace.get('failedItems', []):
                            msg += f"  • {failed}\n"
                    
                    msg += "\nWould you like to:\n"
                    msg += "1. Open the export folder?\n"
                    msg += "2. Re-download (run authentication again)?\n"
                    msg += "3. Index this export in Assessment tab?"
                    
                    reply = QMessageBox.question(self, "Items Already Downloaded", msg,
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Open folder in explorer
                        os.startfile(workspace_path)
                    
                    # Auto-select this export in Assessment tab
                    export_folder_name = latest_export.name
                    index = self.export_dropdown.findText(export_folder_name)
                    if index >= 0:
                        self.export_dropdown.setCurrentIndex(index)
                        self.tabs.setCurrentIndex(4)  # Switch to Assessment tab
                    
                else:
                    QMessageBox.information(self, "Info",
                        f"Workspace folder not found: {workspace_path}\n\n"
                        f"Please run authentication again to download.")
            else:
                QMessageBox.information(self, "Info",
                    "No export folders found. Please run authentication to download.")
        else:
            QMessageBox.information(self, "Info",
                "Downloads folder not found. Please run authentication to download.")
        
    def show_stats(self):
        """Show enhanced statistics with insights"""
        try:
            response = requests.get(f"{self.api_base}/api/assessment-summary")
            if response.status_code == 200:
                data = response.json()
                overview = data.get('overview', {})
                migration = data.get('migration_readiness', {})
                
                msg = "📊 DATABASE STATISTICS\n"
                msg += "=" * 50 + "\n\n"
                
                msg += "OVERVIEW:\n"
                msg += f"  • Workspaces: {overview.get('total_workspaces', 0)}\n"
                msg += f"  • Datasets: {overview.get('total_datasets', 0)}\n"
                msg += f"  • Tables: {overview.get('total_tables', 0)}\n"
                msg += f"  • Data Sources: {overview.get('total_data_sources', 0)}\n\n"
                
                msg += "MIGRATION REQUIREMENTS:\n"
                msg += f"  • Datasets Needing Migration: {overview.get('datasets_needing_migration', 0)}\n"
                msg += f"  • Data Sources to Migrate: {overview.get('sources_needing_migration', 0)}\n\n"
                
                msg += "COMPLEXITY ANALYSIS:\n"
                msg += f"  • High Complexity: {migration.get('high_complexity', 0)} datasets\n"
                msg += f"  • Medium Complexity: {migration.get('medium_complexity', 0)} datasets\n"
                msg += f"  • Low Complexity: {migration.get('low_complexity', 0)} datasets\n"
                    
                QMessageBox.information(self, "Statistics", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load stats:\n{str(e)}")
    
    def auto_scan_downloads(self):
        """Auto-scan Downloads folder on startup"""
        self.scan_downloads_folder()
        # Auto-load dashboard if DB has data
        self.load_assessment_dashboard()
        # Sync initial path to Upload to Fabric tab
        if hasattr(self, 'fabric_upload_tab'):
            export_path = self.export_path_input.text() or self.export_dropdown.currentText()
            if export_path and export_path not in ["Downloads folder not found", "No FabricExport folders found"]:
                self.fabric_upload_tab.set_folder_path(export_path)
    
    def scan_downloads_folder(self):
        """Scan Downloads folder for FabricExport folders"""
        self.export_dropdown.clear()
        
        if not self.downloads_base.exists():
            self.export_dropdown.addItem("Downloads folder not found")
            return
        
        # Find all FabricExport folders (load parent folder, not Processed_Data)
        export_folders = []
        try:
            for item in self.downloads_base.iterdir():
                if item.is_dir() and item.name.startswith("FabricExport_"):
                    # Add the parent FabricExport folder directly
                    export_folders.append(str(item))
        except Exception as e:
            print(f"Error scanning downloads: {e}")
        
        if export_folders:
            for folder in sorted(export_folders, reverse=True):  # Most recent first
                self.export_dropdown.addItem(folder)
            self.statusBar().showMessage(f"Found {len(export_folders)} export(s) in Downloads")
        else:
            self.export_dropdown.addItem("No FabricExport folders found")
            self.statusBar().showMessage("No exports found - use Download tab first")
    
    def refresh_assessment_dropdown(self):
        """Refresh the assessment dropdown to show newly created export folders"""
        self.scan_downloads_folder()
        logging.info("Assessment dropdown refreshed")
    
    def on_export_selected(self, folder_path):
        """Handle export selection from dropdown"""
        if folder_path and folder_path not in ["Downloads folder not found", "No FabricExport folders found"]:
            self.export_path_input.setText(folder_path)
            # Sync to Upload to Fabric tab
            if hasattr(self, 'fabric_upload_tab'):
                self.fabric_upload_tab.set_folder_path(folder_path)
    
    def check_api_health(self):
        """Check if backend API is running"""
        try:
            response = requests.get(f"{self.api_base}/", timeout=2)
            if response.status_code == 200:
                logging.info("Backend API is healthy")
            else:
                logging.warning(f"Backend API returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            logging.error("Backend API is not responding - features may not work")
            QMessageBox.warning(self, "API Connection Issue",
                "The backend server is not responding.\n\n"
                "Some features may not work correctly.\n\n"
                "Try restarting the application. If the problem persists, "
                "check the log file for details.")
        except Exception as e:
            logging.error(f"API health check failed: {e}")
    
    def open_azure_setup_guide(self):
        """Open the Azure App Setup guide"""
        if getattr(sys, 'frozen', False):
            # Running as exe - guide should be in same directory
            guide_path = Path(sys.argv[0]).parent / "AZURE_APP_SETUP.md"
        else:
            # Running from source
            guide_path = Path(__file__).parent.parent.parent / "AZURE_APP_SETUP.md"
        
        if guide_path.exists():
            # Open with default markdown viewer or text editor
            if sys.platform == 'win32':
                os.startfile(guide_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', guide_path])
            else:
                subprocess.run(['xdg-open', guide_path])
        else:
            QMessageBox.warning(self, "Guide Not Found",
                f"Azure App Setup guide not found at:\n{guide_path}\n\n"
                "Please visit: https://learn.microsoft.com/power-bi/developer/automation/api-authentication")
    
    def open_user_guide(self):
        """Open the User Guide (HTML format)"""
        # Try HTML first, fallback to MD
        if getattr(sys, 'frozen', False):
            # Running as exe - guide should be in same directory
            html_path = Path(sys.argv[0]).parent / "USER_GUIDE.html"
            md_path = Path(sys.argv[0]).parent / "USER_GUIDE.md"
        else:
            # Running from source
            html_path = Path(__file__).parent.parent.parent / "USER_GUIDE.html"
            md_path = Path(__file__).parent.parent.parent / "USER_GUIDE.md"
        
        # Prefer HTML, fallback to MD
        if html_path.exists():
            guide_path = html_path
        elif md_path.exists():
            guide_path = md_path
        else:
            QMessageBox.warning(self, "User Guide Not Found",
                f"User Guide not found. Searched for:\n• {html_path}\n• {md_path}")
            return
        
        # Open with default application
        try:
            if sys.platform == 'win32':
                os.startfile(guide_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', guide_path])
            else:
                subprocess.run(['xdg-open', guide_path])
        except Exception as e:
            QMessageBox.warning(self, "Error Opening Guide",
                f"Could not open User Guide:\n{e}\n\nFile location:\n{guide_path}")
    
    def clear_logs(self):
        """Clear all application logs"""
        reply = QMessageBox.question(self, "Clear Logs",
            "Are you sure you want to clear all logs?\n\n"
            "This will:\n"
            "• Clear the application log file (app.log)\n"
            "• Clear all UI results panels\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear the app.log file
                log_root = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'PowerBI Migration Toolkit' / 'logs'
                app_log_file = log_root / 'app.log'
                
                if app_log_file.exists():
                    # Clear the log file content
                    with open(app_log_file, 'w', encoding='utf-8') as f:
                        f.write(f"Log file cleared at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # Clear all results text widgets (UI panels)
                if hasattr(self, 'assessment_results'):
                    self.assessment_results.clear()
                if hasattr(self, 'migration_results'):
                    self.migration_results.clear()
                if hasattr(self, 'rename_results'):
                    self.rename_results.clear()
                if hasattr(self, 'col_rename_results'):
                    self.col_rename_results.clear()
                if hasattr(self, 'publish_results'):
                    self.publish_results.clear()
                
                self.config_status.setText("✓ Logs cleared successfully!\n(app.log and all UI panels)")
                self.config_status.setStyleSheet("padding: 10px; font-weight: bold; color: green;")
                
                logging.info("Logs cleared by user")
                
                # Clear status after 3 seconds
                QTimer.singleShot(3000, lambda: self.config_status.setText(""))
                
            except Exception as e:
                self.config_status.setText(f"✗ Failed to clear logs: {str(e)}")
                self.config_status.setStyleSheet("padding: 10px; font-weight: bold; color: red;")
                QMessageBox.critical(self, "Clear Error", f"Failed to clear logs:\n{str(e)}")
    
    def export_logs(self):
        """Export logs to a text file"""
        from datetime import datetime
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"pbip_studio_logs_{timestamp}.txt"
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get the app.log file path
                log_root = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'PowerBI Migration Toolkit' / 'logs'
                app_log_file = log_root / 'app.log'
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write("PBIP Studio - Application Logs Export\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # Export from app.log file
                    if app_log_file.exists():
                        f.write("\n" + "=" * 80 + "\n")
                        f.write("APPLICATION LOG FILE (app.log)\n")
                        f.write(f"Location: {app_log_file}\n")
                        f.write("=" * 80 + "\n")
                        try:
                            with open(app_log_file, 'r', encoding='utf-8') as log_f:
                                f.write(log_f.read())
                        except Exception as e:
                            f.write(f"Error reading app.log: {str(e)}\n")
                        f.write("\n")
                    else:
                        f.write("\n[WARNING] app.log file not found at: {app_log_file}\n\n")
                    
                    # Export UI Results Panels (for recent operation details)
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("UI RESULTS PANELS (Recent Operations)\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # Export Assessment logs
                    if hasattr(self, 'assessment_results') and self.assessment_results.toPlainText():
                        f.write("\n" + "-" * 80 + "\n")
                        f.write("ASSESSMENT RESULTS\n")
                        f.write("-" * 80 + "\n")
                        f.write(self.assessment_results.toPlainText())
                        f.write("\n")
                    
                    # Export Migration logs
                    if hasattr(self, 'migration_results') and self.migration_results.toPlainText():
                        f.write("\n" + "-" * 80 + "\n")
                        f.write("MIGRATION RESULTS\n")
                        f.write("-" * 80 + "\n")
                        f.write(self.migration_results.toPlainText())
                        f.write("\n")
                    
                    # Export Table Rename logs
                    if hasattr(self, 'rename_results') and self.rename_results.toPlainText():
                        f.write("\n" + "-" * 80 + "\n")
                        f.write("TABLE RENAME RESULTS\n")
                        f.write("-" * 80 + "\n")
                        f.write(self.rename_results.toPlainText())
                        f.write("\n")
                    
                    # Export Column Rename logs
                    if hasattr(self, 'col_rename_results') and self.col_rename_results.toPlainText():
                        f.write("\n" + "-" * 80 + "\n")
                        f.write("COLUMN RENAME RESULTS\n")
                        f.write("-" * 80 + "\n")
                        f.write(self.col_rename_results.toPlainText())
                        f.write("\n")
                    
                    # Export Publish logs
                    if hasattr(self, 'publish_results') and self.publish_results.toPlainText():
                        f.write("\n" + "-" * 80 + "\n")
                        f.write("PUBLISH RESULTS\n")
                        f.write("-" * 80 + "\n")
                        f.write(self.publish_results.toPlainText())
                        f.write("\n")
                
                self.config_status.setText(f"✓ Logs exported successfully to:\n{file_path}")
                self.config_status.setStyleSheet("padding: 10px; font-weight: bold; color: green;")
                
                QMessageBox.information(self, "Export Complete",
                    f"Logs exported successfully!\n\n"
                    f"File: {file_path}\n\n"
                    f"Includes:\n"
                    f"• Complete application log (app.log)\n"
                    f"• Recent UI operation results")
                
            except Exception as e:
                self.config_status.setText(f"✗ Failed to export logs: {str(e)}")
                self.config_status.setStyleSheet("padding: 10px; font-weight: bold; color: red;")
                QMessageBox.critical(self, "Export Error", f"Failed to export logs:\n{str(e)}")
    
    def _update_header_logo(self):
        """Update header logo based on current theme"""
        if hasattr(self, 'header_logo_label'):
            logo_path = self.theme_manager.get_logo_path(128)
            if logo_path.exists():
                pixmap = QPixmap(str(logo_path))
                self.header_logo_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    
    def _get_tab_icon_color(self):
        """Get icon color based on current theme"""
        return 'white' if self.theme_manager.get_current_theme() == 'dark' else '#2d2d2d'
    
    def _update_tab_icons(self):
        """Update all tab icons based on current theme"""
        color = self._get_tab_icon_color()
        
        # Map of tab indices to their icons
        tab_icons = {
            0: ('fa5s.cog', 'Configuration'),
            1: ('fa5s.cloud-download-alt', 'Download from Fabric'),
            2: ('fa5s.file-import', 'Assessment'),
            3: ('fa5s.exchange-alt', 'Data Source Migration'),
            4: ('fa5s.search-plus', 'Migration Preview'),
            5: ('fa5s.edit', 'Rename Tables'),
            6: ('fa5s.columns', 'Rename Columns'),
            7: ('fa5s.cloud-upload-alt', 'Upload to Fabric'),
            8: ('fa5s.history', 'Restore'),
        }
        
        for index, (icon_name, _) in tab_icons.items():
            if index < self.tabs.count():
                self.tabs.setTabIcon(index, qta.icon(icon_name, color=color))
    
    def apply_theme(self):
        """Apply current theme to the application"""
        stylesheet = self.theme_manager.get_stylesheet()
        self.setStyleSheet(stylesheet)
        
        # Update label colors based on theme
        if hasattr(self, 'backup_count_label'):
            color = self.theme_manager.get_text_color("muted")
            self.backup_count_label.setStyleSheet(f"color: {color}; font-size: 10px;")
        
        # Update copyright label
        for child in self.findChildren(QLabel):
            if "2024-2026 Taik18" in child.text():
                color = self.theme_manager.get_text_color("secondary")
                child.setStyleSheet(f"color: {color}; font-size: 10px; font-style: italic;")
        
        # Update title label
        for child in self.findChildren(QLabel):
            if child.text() == "PBIP Studio" and child.font().pointSize() == 20:
                child.setStyleSheet("color: #0078D4; margin-left: 10px;")
        
        # Re-apply button styles that need special colors
        self.apply_button_styles()
        
        logging.info(f"Applied {self.theme_manager.get_current_theme()} theme")
    
    def apply_button_styles(self):
        """Apply special button styles that override theme defaults"""
        # Find and update save buttons
        for button in self.findChildren(QPushButton):
            button_text = button.text().lower()
            
            if "save" in button_text and "config" in button_text:
                style = self.theme_manager.get_button_style("success")
                if style:
                    button.setStyleSheet(style + " padding: 10px 20px; font-size: 13px; border-radius: 5px;")
            
            elif "clear" in button_text and "log" in button_text:
                style = self.theme_manager.get_button_style("danger")
                if style:
                    button.setStyleSheet(style + " padding: 8px 16px; font-size: 12px; border-radius: 4px;")
            
            elif "export" in button_text and "log" in button_text:
                style = self.theme_manager.get_button_style("info")
                if style:
                    button.setStyleSheet(style + " padding: 8px 16px; font-size: 12px; border-radius: 4px;")
            
            elif "start" in button_text and "download" in button_text:
                style = self.theme_manager.get_button_style("primary")
                if style:
                    button.setStyleSheet(style + " padding: 12px 24px; font-size: 14px; border-radius: 5px;")
            
            elif "migrate" in button_text:
                style = self.theme_manager.get_button_style("warning")
                if style:
                    button.setStyleSheet(style + " padding: 12px 24px; font-size: 14px; border-radius: 5px;")
            
            elif "upload" in button_text or "publish" in button_text:
                style = self.theme_manager.get_button_style("info")
                if style:
                    button.setStyleSheet(style + " padding: 12px 24px; font-size: 14px; border-radius: 5px;")
    
    def on_theme_changed(self, theme):
        """Handle theme change signal"""
        self.apply_theme()
        self.update_theme_icon()
        self._update_header_logo()  # Update logo for new theme
        self._update_tab_icons()  # Update tab icons for new theme
        
        # Notify child tabs about theme change
        if hasattr(self, 'fabric_cli_tab'):
            self.fabric_cli_tab.apply_theme(theme)
        
        if hasattr(self, 'fabric_upload_tab'):
            self.fabric_upload_tab.apply_theme(theme)
        
        self.statusBar().showMessage(f"Theme changed to {theme} mode", 2000)
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = self.theme_manager.toggle_theme()
        logging.info(f"User toggled theme to: {new_theme}")
    
    def update_theme_icon(self):
        """Update theme toggle button icon based on current theme"""
        current_theme = self.theme_manager.get_current_theme()
        if current_theme == "dark":
            # Show sun icon when in dark mode (clicking will switch to light)
            icon = qta.icon('fa5s.sun', color='#0078D4')
            tooltip = "Switch to Light Mode"
        else:
            # Show moon icon when in light mode (clicking will switch to dark)
            icon = qta.icon('fa5s.moon', color='#0078D4')
            tooltip = "Switch to Dark Mode"
        
        if hasattr(self, 'theme_toggle_btn'):
            self.theme_toggle_btn.setIcon(icon)
            self.theme_toggle_btn.setToolTip(tooltip)


