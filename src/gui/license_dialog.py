"""
License Activation Dialog for PowerBI Desktop App
Shows on first startup or when license expires
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QGroupBox,
    QMessageBox, QApplication, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon
import qtawesome as qta
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from utils.license_manager import LicenseManager
from utils.theme_manager import get_theme_manager


class LicenseDialog(QDialog):
    """Dialog for license activation and management"""
    
    def __init__(self, parent=None, current_license=None):
        super().__init__(parent)
        self.license_manager = LicenseManager()
        self.theme_manager = get_theme_manager()
        self.current_license = current_license
        self.setWindowTitle("PowerBI Desktop App - License Activation")
        self.setModal(True)
        self.setMinimumWidth(600)
        
        # Apply theme to dialog
        self.setStyleSheet(self.theme_manager.get_stylesheet())
        
        # Set window icon
        if getattr(sys, 'frozen', False):
            icon_path = Path(sys.argv[0]).parent / 'logos' / 'logo pbip studio Black 128.png'
        else:
            icon_path = Path(__file__).parent.parent.parent / 'logos' / 'logo pbip studio Black 128.png'
        
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Logo and Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load theme-appropriate logo
        try:
            from src.utils.theme_manager import ThemeManager
            theme_manager = ThemeManager()
            logo_path = theme_manager.get_logo_path(128)
        except:
            # Fallback to transparent logo
            if getattr(sys, 'frozen', False):
                logo_path = Path(sys.argv[0]).parent / 'logos' / 'logo pbip studio Transparent 512.png'
            else:
                logo_path = Path(__file__).parent.parent.parent / 'logos' / 'logo pbip studio Transparent 512.png'
        
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                # Scale logo to reasonable size
                scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
        
        header_layout.addWidget(logo_label)
        
        # Header text
        header = QLabel("PowerBI Migration Toolkit")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(header)
        
        # Add header layout to main layout
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
        # Status section
        if self.current_license and not self.current_license.get('valid'):
            status_box = QGroupBox("License Status")
            status_layout = QVBoxLayout()
            
            error_msg = self.current_license.get('error', 'No license found')
            status_label = QLabel(f"⚠️ {error_msg}")
            status_label.setStyleSheet("color: #d32f2f; padding: 10px; font-size: 11pt;")
            status_label.setWordWrap(True)
            status_layout.addWidget(status_label)
            
            status_box.setLayout(status_layout)
            layout.addWidget(status_box)
        
        # Machine ID display
        machine_box = QGroupBox("Machine Information")
        machine_layout = QVBoxLayout()
        
        # Machine ID with copy button
        machine_id_layout = QHBoxLayout()
        
        machine_label = QLabel(f"Machine ID: {self.license_manager.machine_id}")
        machine_label.setStyleSheet("font-family: 'Courier New'; background: transparent; padding: 8px; font-size: 11pt; font-weight: bold;")
        machine_id_layout.addWidget(machine_label)
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setFixedWidth(80)
        copy_btn.setToolTip("Copy Machine ID to clipboard")
        copy_btn.clicked.connect(lambda: self.copy_machine_id())
        style = self.theme_manager.get_button_style("primary")
        copy_btn.setStyleSheet(style + """
            padding: 6px;
            font-size: 10pt;
        """)
        machine_id_layout.addWidget(copy_btn)
        machine_id_layout.addStretch()
        
        machine_layout.addLayout(machine_id_layout)
        
        info_label = QLabel("ℹ️ Send this Machine ID to support@taik18.com to receive your license key")
        if self.theme_manager.get_current_theme() == "dark":
            info_label.setStyleSheet("color: #b0b0b0; font-size: 9pt; margin-top: 5px;")
        else:
            info_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 5px;")
        info_label.setWordWrap(True)
        machine_layout.addWidget(info_label)
        
        machine_box.setLayout(machine_layout)
        layout.addWidget(machine_box)
        
        # License key input
        key_box = QGroupBox("Enter License Key")
        key_layout = QVBoxLayout()
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("PBMT-XXXXX-XXXXX-XXXXX")
        self.key_input.setFont(QFont("Courier New", 11))
        self.key_input.textChanged.connect(self.format_license_key)
        key_layout.addWidget(self.key_input)
        
        hint_label = QLabel("Enter the license key you received via email after purchase")
        if self.theme_manager.get_current_theme() == "dark":
            hint_label.setStyleSheet("color: #b0b0b0; font-size: 9pt; margin-top: 5px;")
        else:
            hint_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 5px;")
        key_layout.addWidget(hint_label)
        
        key_box.setLayout(key_layout)
        layout.addWidget(key_box)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.activate_btn = QPushButton("Activate License")
        self.activate_btn.setMinimumWidth(150)
        self.activate_btn.setMinimumHeight(35)
        self.activate_btn.clicked.connect(self.activate_license)
        style = self.theme_manager.get_button_style("info")
        self.activate_btn.setStyleSheet(style + """
            font-size: 11pt;
            font-weight: bold;
        """)
        button_layout.addWidget(self.activate_btn)
        
        self.cancel_btn = QPushButton("Exit")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setMinimumHeight(35)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Purchase info
        delivery_note = QLabel("📧 License keys are sent via email within 1-2 hours (max 24 hours) after purchase")
        delivery_note.setStyleSheet("color: #0078D4; font-size: 9pt; margin-top: 10px; font-weight: 500;")
        delivery_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delivery_note.setWordWrap(True)
        layout.addWidget(delivery_note)
        
        purchase_label = QLabel("Don't have a license key? Contact: support@taik18.com")
        if self.theme_manager.get_current_theme() == "dark":
            purchase_label.setStyleSheet("color: #b0b0b0; font-size: 9pt; margin-top: 5px;")
        else:
            purchase_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 5px;")
        purchase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(purchase_label)
        
        self.setLayout(layout)
    
    def copy_machine_id(self):
        """Copy machine ID to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.license_manager.machine_id)
        QMessageBox.information(
            self,
            "Copied!",
            f"Machine ID copied to clipboard:\n\n{self.license_manager.machine_id}\n\n"
            f"Send this to support@taik18.com to receive your license key."
        )
    
    def format_license_key(self):
        """Auto-format license key as user types"""
        text = self.key_input.text().upper().replace(' ', '').replace('-', '')
        
        # Only keep alphanumeric characters
        text = ''.join(c for c in text if c.isalnum())
        
        # Don't auto-format if starts with PBMT
        if text.startswith('PBMT'):
            return
        
        self.key_input.blockSignals(True)
        self.key_input.setText(text)
        self.key_input.blockSignals(False)
    
    def activate_license(self):
        """Activate the entered license key"""
        license_key = self.key_input.text().strip()  # Don't convert to upper - base64 is case-sensitive!
        
        if not license_key:
            QMessageBox.warning(self, "Invalid Input", "Please enter a license key")
            return
        
        # Show progress
        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Activating...")
        QApplication.processEvents()
        
        # Attempt activation
        result = self.license_manager.activate_license(license_key)
        
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("Activate License")
        
        if result.get('valid'):
            expiry = result.get('expiry', '')
            days = result.get('days_remaining', 0)
            
            QMessageBox.information(
                self,
                "Activation Successful",
                f"✓ License activated successfully!\n\n"
                f"Email: {result.get('email', 'N/A')}\n"
                f"Valid for: {days} days\n"
                f"Expires: {expiry[:10] if expiry else 'N/A'}\n\n"
                f"Thank you for your purchase!"
            )
            self.accept()
        else:
            error = result.get('error', 'Unknown error')
            QMessageBox.critical(
                self,
                "Activation Failed",
                f"Failed to activate license:\n\n{error}\n\n"
                f"Please check your license key or contact support."
            )


class LicenseInfoDialog(QDialog):
    """Dialog to display current license information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_manager = LicenseManager()
        self.theme_manager = get_theme_manager()
        self.setWindowTitle("License Information")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        # Set window icon
        if getattr(sys, 'frozen', False):
            icon_path = Path(sys.argv[0]).parent / 'logos' / 'logo pbip studio Black 128.png'
        else:
            icon_path = Path(__file__).parent.parent.parent / 'logos' / 'logo pbip studio Black 128.png'
        
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Get license info
        license_info = self.license_manager.get_current_license()
        
        # Header
        header = QLabel("Current License")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        if license_info.get('valid'):
            # License details
            details_box = QGroupBox("License Details")
            details_layout = QVBoxLayout()
            
            # Status
            status_label = QLabel("✓ Active")
            status_label.setStyleSheet("color: #388e3c; font-size: 12pt; font-weight: bold;")
            details_layout.addWidget(status_label)
            
            # Info grid
            info_text = f"""
<table style="width: 100%; margin-top: 10px;">
    <tr><td style="color: #666; padding: 5px;"><b>Email:</b></td><td style="padding: 5px;">{license_info.get('email', 'N/A')}</td></tr>
    <tr><td style="color: #666; padding: 5px;"><b>Expires:</b></td><td style="padding: 5px;">{license_info.get('expiry', '')[:10]}</td></tr>
    <tr><td style="color: #666; padding: 5px;"><b>Days Remaining:</b></td><td style="padding: 5px;">{license_info.get('days_remaining', 0)} days</td></tr>
    <tr><td style="color: #666; padding: 5px;"><b>Machine ID:</b></td><td style="padding: 5px; font-family: 'Courier New';">{license_info.get('machine_id', 'N/A')}</td></tr>
    <tr><td style="color: #666; padding: 5px;"><b>Activated:</b></td><td style="padding: 5px;">{license_info.get('activated_at', '')[:10]}</td></tr>
</table>
"""
            info_label = QLabel(info_text)
            info_label.setTextFormat(Qt.TextFormat.RichText)
            details_layout.addWidget(info_label)
            
            # Warning if expiring soon
            days_remaining = license_info.get('days_remaining', 0)
            if days_remaining < 30:
                warning_label = QLabel(f"⚠️ Your license expires in {days_remaining} days. Contact support for renewal.")
                warning_label.setStyleSheet("color: #f57c00; background: #fff3e0; padding: 10px; border-radius: 4px; margin-top: 10px;")
                warning_label.setWordWrap(True)
                details_layout.addWidget(warning_label)
            
            details_box.setLayout(details_layout)
            layout.addWidget(details_box)
            
            # Revoke button
            revoke_box = QGroupBox("License Management")
            revoke_layout = QVBoxLayout()
            
            revoke_label = QLabel("To move your license to a new computer, revoke it here first.")
            revoke_label.setStyleSheet("color: #666; font-size: 9pt;")
            revoke_label.setWordWrap(True)
            revoke_layout.addWidget(revoke_label)
            
            revoke_btn = QPushButton("🗑️ Revoke License")
            revoke_btn.clicked.connect(self.revoke_license)
            style = self.theme_manager.get_button_style("danger")
            revoke_btn.setStyleSheet(style + " padding: 8px; border-radius: 4px; margin-top: 5px;")
            revoke_layout.addWidget(revoke_btn)
            
            revoke_box.setLayout(revoke_layout)
            layout.addWidget(revoke_box)
            
        else:
            # No valid license
            error_label = QLabel(f"⚠️ {license_info.get('error', 'No license found')}")
            error_label.setStyleSheet("color: #d32f2f; background: #ffebee; padding: 15px; border-radius: 4px;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(35)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def revoke_license(self):
        """Revoke the current license"""
        reply = QMessageBox.question(
            self,
            "Confirm Revocation",
            "Are you sure you want to revoke this license?\n\n"
            "The application will close and you'll need to re-activate on next launch.\n"
            "You can then activate on a different machine.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.license_manager.revoke_license():
                QMessageBox.information(
                    self,
                    "License Revoked",
                    "License has been revoked successfully.\n"
                    "The application will now close."
                )
                # Exit application
                QApplication.quit()
            else:
                QMessageBox.warning(
                    self,
                    "Revocation Failed",
                    "Failed to revoke license. Please try again."
                )


if __name__ == '__main__':
    """Test the dialog"""
    app = QApplication(sys.argv)
    
    # Test activation dialog
    dialog = LicenseDialog()
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        # Show info dialog
        info_dialog = LicenseInfoDialog()
        info_dialog.exec()
    
    sys.exit()
