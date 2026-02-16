"""
Theme Manager for Power BI Migration Toolkit
Handles light/dark theme switching with Windows theme detection
"""

import winreg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
import logging
import os


class ThemeManager(QObject):
    """Manages application theme and provides signals for theme changes"""
    
    theme_changed = pyqtSignal(str)  # Emits 'light' or 'dark'
    
    def __init__(self):
        super().__init__()
        self._current_theme = self.detect_windows_theme()
        
    def detect_windows_theme(self):
        """Detect Windows theme (light/dark mode)"""
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except Exception as e:
            logging.warning(f"Could not detect Windows theme: {e}")
            return "dark"  # Default to dark
    
    def get_current_theme(self):
        """Get current theme"""
        return self._current_theme
    
    def set_theme(self, theme):
        """Set theme ('light' or 'dark')"""
        if theme not in ['light', 'dark']:
            raise ValueError("Theme must be 'light' or 'dark'")
        
        if theme != self._current_theme:
            self._current_theme = theme
            self.theme_changed.emit(theme)
            logging.info(f"Theme changed to: {theme}")
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme
    
    def get_stylesheet(self):
        """Get complete application stylesheet for current theme"""
        if self._current_theme == "light":
            return self._get_light_stylesheet()
        else:
            return self._get_dark_stylesheet()
    
    def get_logo_path(self, size=128):
        """Get theme-appropriate logo path
        
        Args:
            size: Logo size (32, 128, 512)
            
        Returns:
            Path to logo file appropriate for current theme
        """
        from pathlib import Path
        import sys
        
        # Determine base path (different for frozen/development)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.argv[0]).parent / 'logos'
        else:
            base_path = Path(__file__).parent.parent.parent / 'logos'
        
        # Always use transparent logo - works for both light and dark modes
        logo_name = f"logo pbip studio Transparent {size}.png"
        logo_path = base_path / logo_name
        
        # Fallback to white logo if transparent not found
        if not logo_path.exists():
            fallback = base_path / f"logo pbip studio White {size}.png"
            if fallback.exists():
                return fallback
        
        return logo_path
    
    def _get_dark_stylesheet(self):
        """Dark theme stylesheet"""
        return """
            QMainWindow {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            
            QWidget#centralWidget {
                background-color: #1e1e1e;
                border: none;
            }
            
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #252525;
            }
            
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #b0b0b0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background-color: #252525;
                color: #ffffff;
                font-weight: bold;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
                color: #e0e0e0;
            }
            
            QGroupBox {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                margin-top: 6px;
                padding-top: 6px;
                color: #e0e0e0;
                font-weight: normal;
                font-size: 9pt;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #0078D4;
                font-weight: bold;
            }
            
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 3px 6px;
                min-height: 18px;
            }
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #0078D4;
            }
            
            QComboBox {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 3px 6px;
                padding-right: 20px;
                min-height: 18px;
            }
            
            QComboBox:hover {
                border: 1px solid #0078D4;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 16px;
                border: none;
            }
            
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #b0b0b0;
                margin-right: 2px;
            }
            
            QComboBox:hover::down-arrow {
                border-top-color: #0078D4;
            }
            
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #0078D4;
                selection-color: #ffffff;
                border: 1px solid #3a3a3a;
                outline: none;
                padding: 2px;
            }
            
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 4px 8px;
                min-height: 18px;
                font-size: 9pt;
            }
            
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #0078D4;
            }
            
            QPushButton:pressed {
                background-color: #252525;
            }
            
            QPushButton:disabled {
                background-color: #1e1e1e;
                color: #666666;
                border: 1px solid #2d2d2d;
            }
            
            QTableWidget, QTreeWidget {
                background-color: #252525;
                alternate-background-color: #2d2d2d;
                color: #e0e0e0;
                gridline-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                font-size: 8pt;
            }
            
            QTableWidget::item, QTreeWidget::item {
                padding: 0px 3px;
                border: none;
                height: 20px;
            }
            
            QTableWidget::item:selected, QTreeWidget::item:selected {
                background-color: #0078D4;
                color: #ffffff;
            }
            
            QTreeWidget::branch {
                background: #252525;
            }
            
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 5px 6px;
                border: none;
                border-bottom: 1px solid #3a3a3a;
                border-right: 1px solid #3a3a3a;
                font-weight: normal;
                font-size: 8pt;
            }
            
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                text-align: center;
                color: #e0e0e0;
            }
            
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 2px;
            }
            
            QCheckBox {
                color: #e0e0e0;
                spacing: 6px;
            }
            
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #5a5a5a;
                border-radius: 2px;
                background-color: #1e1e1e;
            }
            
            QCheckBox::indicator:hover {
                border: 1px solid #0078D4;
                background-color: #2d2d2d;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078D4;
                border: 1px solid #0078D4;
            }
            
            QCheckBox::indicator:checked:hover {
                background-color: #005a9e;
                border: 1px solid #005a9e;
            }
            
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 12px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: #3a3a3a;
                border-radius: 6px;
                min-width: 20px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: #4a4a4a;
            }
            
            QStatusBar {
                background-color: #252525;
                color: #b0b0b0;
            }
            
            QToolTip {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                padding: 5px;
            }
        """
    
    def _get_light_stylesheet(self):
        """Light theme stylesheet"""
        return """
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }
            
            QWidget {
                background-color: #ffffff;
                color: #202020;
            }
            
            QWidget#centralWidget {
                background-color: #ffffff;
                border: none;
            }
            
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background-color: #f5f5f5;
            }
            
            QTabBar::tab {
                background-color: #e8e8e8;
                color: #404040;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background-color: #f5f5f5;
                color: #000000;
                font-weight: bold;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #d0d0d0;
                color: #000000;
            }
            
            QGroupBox {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                margin-top: 6px;
                padding-top: 6px;
                color: #000000;
                font-weight: normal;
                font-size: 9pt;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #0078D4;
                font-weight: bold;
            }
            
            QLabel {
                color: #000000;
                background-color: transparent;
            }
            
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 3px 6px;
                min-height: 18px;
            }
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #0078D4;
            }
            
            QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 3px 6px;
                padding-right: 20px;
                min-height: 18px;
            }
            
            QComboBox:hover {
                border: 1px solid #0078D4;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 16px;
                border: none;
            }
            
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #606060;
                margin-right: 2px;
            }
            
            QComboBox:hover::down-arrow {
                border-top-color: #0078D4;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #0078D4;
                selection-color: #ffffff;
                border: 1px solid #c0c0c0;
                outline: none;
                padding: 2px;
            }
            
            QPushButton {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 4px 8px;
                min-height: 18px;
                font-size: 9pt;
            }
            
            QPushButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #0078D4;
            }
            
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #a0a0a0;
                border: 1px solid #d0d0d0;
            }
            
            QTableWidget, QTreeWidget {
                background-color: #ffffff;
                alternate-background-color: #f8f8f8;
                color: #000000;
                gridline-color: #d0d0d0;
                border: 1px solid #d0d0d0;
                font-size: 8pt;
            }
            
            QTableWidget::item, QTreeWidget::item {
                padding: 0px 3px;
                border: none;
                height: 20px;
            }
            
            QTableWidget::item:selected, QTreeWidget::item:selected {
                background-color: #0078D4;
                color: #ffffff;
            }
            
            QTreeWidget::branch {
                background: #ffffff;
            }
            
            QHeaderView::section {
                background-color: #f0f0f0;
                color: #000000;
                padding: 5px 6px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                border-right: 1px solid #d0d0d0;
                font-weight: normal;
                font-size: 8pt;
            }
            
            QProgressBar {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                text-align: center;
                color: #000000;
            }
            
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 2px;
            }
            
            QCheckBox {
                color: #000000;
                spacing: 6px;
            }
            
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #a0a0a0;
                border-radius: 2px;
                background-color: #ffffff;
            }
            
            QCheckBox::indicator:hover {
                border: 1px solid #0078D4;
                background-color: #f5f5f5;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078D4;
                border: 1px solid #0078D4;
            }
            
            QCheckBox::indicator:checked:hover {
                background-color: #005a9e;
                border: 1px solid #005a9e;
            }
            
            QScrollBar:vertical {
                background-color: #f5f5f5;
                width: 12px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            
            QScrollBar:horizontal {
                background-color: #f5f5f5;
                height: 12px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
            
            QStatusBar {
                background-color: #f5f5f5;
                color: #404040;
            }
            
            QToolTip {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c0c0c0;
                padding: 5px;
            }
        """
    
    def get_button_style(self, button_type="default", theme=None):
        """Get button-specific styles that override the base stylesheet"""
        if theme is None:
            theme = self._current_theme
        
        if theme == "dark":
            return self._get_dark_button_style(button_type)
        else:
            return self._get_light_button_style(button_type)
    
    def _get_dark_button_style(self, button_type):
        """Dark theme button styles"""
        styles = {
            "primary": """
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """,
            "success": """
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
            """,
            "warning": """
                QPushButton {
                    background-color: #f39c12;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
                QPushButton:pressed {
                    background-color: #d35400;
                }
            """,
            "info": """
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """,
        }
        return styles.get(button_type, "")
    
    def _get_light_button_style(self, button_type):
        """Light theme button styles"""
        styles = {
            "primary": """
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QPushButton:disabled {
                    background-color: #e0e0e0;
                    color: #a0a0a0;
                }
            """,
            "success": """
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
            """,
            "warning": """
                QPushButton {
                    background-color: #f39c12;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
                QPushButton:pressed {
                    background-color: #d35400;
                }
            """,
            "info": """
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """,
        }
        return styles.get(button_type, "")
    
    def get_text_color(self, element_type="primary"):
        """Get text color for specific element types"""
        if self._current_theme == "dark":
            colors = {
                "primary": "#e0e0e0",
                "secondary": "#b0b0b0",
                "accent": "#0078D4",
                "success": "#27ae60",
                "danger": "#e74c3c",
                "warning": "#f39c12",
                "muted": "#7f8c8d"
            }
        else:
            colors = {
                "primary": "#000000",
                "secondary": "#404040",
                "accent": "#0078D4",
                "success": "#27ae60",
                "danger": "#e74c3c",
                "warning": "#f39c12",
                "muted": "#666666"
            }
        return colors.get(element_type, colors["primary"])
    
    def get_icon_color(self):
        """Get icon color for current theme"""
        return "#0078D4"  # Keep icons blue in both themes for consistency


# Global instance
_theme_manager = None

def get_theme_manager():
    """Get or create global theme manager instance"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
