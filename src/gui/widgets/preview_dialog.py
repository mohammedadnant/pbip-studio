"""
Migration Preview Dialog
Shows diff preview before applying changes
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QGroupBox, QFileDialog, QMessageBox, QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter
import qtawesome as qta
from pathlib import Path
from typing import Dict, List
from gui.widgets.side_by_side_diff import SideBySideDiffViewer


class MQueryHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Power Query M language"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define formats
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#0000FF"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#795E26"))
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#A31515"))
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#008000"))
        self.comment_format.setFontItalic(True)
        
        self.added_format = QTextCharFormat()
        self.added_format.setBackground(QColor("#d4ffd4"))
        self.added_format.setForeground(QColor("#006400"))  # Dark green text
        
        self.removed_format = QTextCharFormat()
        self.removed_format.setBackground(QColor("#ffd4d4"))
        self.removed_format.setForeground(QColor("#DC143C"))  # Red text
        
        # M Query keywords
        self.keywords = [
            'let', 'in', 'if', 'then', 'else', 'error', 'try', 'otherwise',
            'each', 'as', 'is', 'meta', 'type'
        ]
        
        # Common M functions
        self.functions = [
            'Source', 'Sql.Database', 'Snowflake.Databases', 'Excel.Workbook',
            'Csv.Document', 'Json.Document', 'File.Contents', 'Table.PromoteHeaders',
            'Table.TransformColumnTypes', 'Table.SelectColumns'
        ]
    
    def highlightBlock(self, text):
        """Highlight a block of text"""
        # Check for diff markers
        if text.startswith('+'):
            self.setFormat(0, len(text), self.added_format)
            return
        elif text.startswith('-'):
            self.setFormat(0, len(text), self.removed_format)
            return
        
        # Keywords
        for keyword in self.keywords:
            index = text.find(keyword)
            while index >= 0:
                self.setFormat(index, len(keyword), self.keyword_format)
                index = text.find(keyword, index + len(keyword))
        
        # Functions
        for func in self.functions:
            index = text.find(func)
            while index >= 0:
                self.setFormat(index, len(func), self.function_format)
                index = text.find(func, index + len(func))
        
        # Strings
        start_index = 0
        while True:
            start_index = text.find('"', start_index)
            if start_index == -1:
                break
            end_index = text.find('"', start_index + 1)
            if end_index == -1:
                end_index = len(text)
            else:
                end_index += 1
            self.setFormat(start_index, end_index - start_index, self.string_format)
            start_index = end_index


class PreviewDialog(QDialog):
    """Modal dialog showing migration preview with diff viewer"""
    
    def __init__(self, preview_data: Dict, parent=None):
        super().__init__(parent)
        self.preview_data = preview_data
        self.user_approved = False
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(f"🔍 Migration Preview - {self.preview_data['model_name']} ({self.preview_data['source_type_from']} → {self.preview_data['source_type_to']})")
        self.setMinimumSize(1400, 900)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Compact header with minimal info
        self.create_compact_header(layout)
        
        # Main content: Split between file tree and diff viewer
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #3e3e3e;
                width: 2px;
            }
        """)
        
        # Left: File tree
        self.create_file_tree(splitter)
        
        # Right: Diff viewer
        self.create_diff_viewer(splitter)
        
        splitter.setStretchFactor(0, 20)  # 20% for tree
        splitter.setStretchFactor(1, 80)  # 80% for diff
        
        layout.addWidget(splitter, 1)
        
        # Bottom: Action buttons
        self.create_action_buttons(layout)
        
    def create_compact_header(self, layout):
        """Create compact header with minimal info"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: #2d2d2d;
                border-bottom: 1px solid #0078D4;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 8, 15, 8)
        header_layout.setSpacing(20)
        
        summary = self.preview_data['summary']
        
        # Files stat
        files_label = QLabel(f"📁 <b>{summary['total_files']}</b> Files")
        files_label.setStyleSheet("color: #3498db; font-size: 12px; background: transparent;")
        header_layout.addWidget(files_label)
        
        # Tables stat
        tables_label = QLabel(f"📊 <b>{summary['total_tables']}</b> Tables")
        tables_label.setStyleSheet("color: #9b59b6; font-size: 12px; background: transparent;")
        header_layout.addWidget(tables_label)
        
        # Lines changed stat
        lines_label = QLabel(f"📝 <b>{summary['total_lines_changed']}</b> Lines Changed")
        lines_label.setStyleSheet("color: #e67e22; font-size: 12px; background: transparent;")
        header_layout.addWidget(lines_label)
        
        header_layout.addStretch()
        
        # Connection info
        conn_parts = []
        for param, value in summary['connection_changes'].items():
            conn_parts.append(f"{param}={value}")
        conn_text = " | ".join(conn_parts)
        
        conn_label = QLabel(conn_text)
        conn_label.setStyleSheet("color: #b0b0b0; font-size: 11px; background: transparent;")
        header_layout.addWidget(conn_label)
        
        layout.addWidget(header_widget)
    
    def create_file_tree(self, splitter):
        """Create file tree showing all files to be changed"""
        tree_container = QWidget()
        tree_container.setStyleSheet("background: #252526;")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)
        
        # Header
        header_label = QLabel("  📁 Files to Change")
        header_label.setStyleSheet("""
            QLabel {
                background: #2d2d30;
                color: #cccccc;
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                border-bottom: 1px solid #3e3e3e;
            }
        """)
        tree_layout.addWidget(header_label)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["File", "Changes"])
        self.file_tree.setColumnWidth(0, 220)
        self.file_tree.itemSelectionChanged.connect(self.on_file_selected)
        self.file_tree.setStyleSheet("""
            QTreeWidget {
                background: #252526;
                color: #cccccc;
                border: none;
                outline: none;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 8px 5px;
                border-bottom: 1px solid #2d2d30;
            }
            QTreeWidget::item:hover {
                background: #2a2d2e;
            }
            QTreeWidget::item:selected {
                background: #094771;
                color: white;
            }
            QHeaderView::section {
                background: #2d2d30;
                color: #cccccc;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #3e3e3e;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        # Populate tree with files
        for file_change in self.preview_data['files_to_change']:
            item = QTreeWidgetItem(self.file_tree)
            item.setText(0, f"📄 {file_change['table_name']}.tmdl")
            item.setText(1, f"+{file_change['lines_added']} -{file_change['lines_removed']}")
            item.setData(0, Qt.ItemDataRole.UserRole, file_change)
            
            # Color code by change magnitude
            if file_change['lines_changed'] > 10:
                item.setForeground(1, QColor("#f48771"))
            elif file_change['lines_changed'] > 5:
                item.setForeground(1, QColor("#dcdcaa"))
            else:
                item.setForeground(1, QColor("#4ec9b0"))
        
        tree_layout.addWidget(self.file_tree)
        splitter.addWidget(tree_container)
    
    def create_diff_viewer(self, splitter):
        """Create side-by-side diff viewer panel"""
        diff_container = QWidget()
        diff_container.setStyleSheet("background: #1e1e1e;")
        diff_layout = QVBoxLayout(diff_container)
        diff_layout.setContentsMargins(0, 0, 0, 0)
        diff_layout.setSpacing(0)
        
        # Header with navigation
        header_widget = QWidget()
        header_widget.setStyleSheet("background: #2d2d30; border-bottom: 1px solid #3e3e3e;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 8, 15, 8)
        
        self.current_file_label = QLabel("📄 Select a file to preview")
        self.current_file_label.setStyleSheet("font-weight: bold; color: #4ec9b0; font-size: 13px; background: transparent;")
        header_layout.addWidget(self.current_file_label)
        
        header_layout.addStretch()
        
        # Navigation buttons
        self.prev_btn = QPushButton(qta.icon('fa5s.chevron-left', color='#cccccc'), " Previous")
        self.prev_btn.clicked.connect(self.show_previous_file)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: #3e3e42;
                color: #cccccc;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: #505053;
            }
        """)
        header_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton(qta.icon('fa5s.chevron-right', color='#cccccc'), " Next")
        self.next_btn.clicked.connect(self.show_next_file)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: #3e3e42;
                color: #cccccc;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: #505053;
            }
        """)
        header_layout.addWidget(self.next_btn)
        
        diff_layout.addWidget(header_widget)
        
        # Side-by-side diff viewer
        self.diff_viewer = SideBySideDiffViewer()
        diff_layout.addWidget(self.diff_viewer)
        
        splitter.addWidget(diff_container)
    
    def create_action_buttons(self, layout):
        """Create action buttons at bottom"""
        button_widget = QWidget()
        button_widget.setStyleSheet("background: #2d2d30; border-top: 1px solid #3e3e3e;")
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(20, 12, 20, 12)
        button_layout.setSpacing(10)
        
        # Export report button
        export_btn = QPushButton(qta.icon('fa5s.file-export', color='white'), " Export HTML Report")
        export_btn.clicked.connect(self.export_report)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #505053;
                color: white;
                padding: 10px 20px;
                font-size: 13px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #5a5d61;
            }
        """)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton(qta.icon('fa5s.times', color='white'), " Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                font-size: 13px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        button_layout.addWidget(cancel_btn)
        
        # Apply button
        apply_btn = QPushButton(qta.icon('fa5s.check', color='white'), " Apply Changes")
        apply_btn.clicked.connect(self.approve_changes)
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        button_layout.addWidget(apply_btn)
        
        layout.addWidget(button_widget)
    
    def on_file_selected(self):
        """Handle file selection in tree"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
        
        file_change = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        self.show_diff(file_change)
        
    def show_diff(self, file_change: Dict):
        """Display side-by-side diff for selected file"""
        self.current_file_label.setText(f"📄 {file_change['table_name']}.tmdl")
        
        # Get old and new content
        old_content = file_change.get('old_content', '')
        new_content = file_change.get('new_content', '')
        
        # If no changes, show info
        if old_content == new_content:
            # Show empty comparison
            self.diff_viewer.set_diff("No changes", "No changes")
            return
        
        # Display side-by-side comparison
        self.diff_viewer.set_diff(old_content, new_content)
        
    def show_previous_file(self):
        """Navigate to previous file"""
        current = self.file_tree.currentItem()
        if current:
            index = self.file_tree.indexOfTopLevelItem(current)
            if index > 0:
                self.file_tree.setCurrentItem(self.file_tree.topLevelItem(index - 1))
        
    def show_next_file(self):
        """Navigate to next file"""
        current = self.file_tree.currentItem()
        if current:
            index = self.file_tree.indexOfTopLevelItem(current)
            if index < self.file_tree.topLevelItemCount() - 1:
                self.file_tree.setCurrentItem(self.file_tree.topLevelItem(index + 1))
        
    def export_report(self):
        """Export preview to HTML report"""
        from utils.data_source_migration import export_preview_report
        
        # Ask for save location
        default_filename = f"Migration_Preview_{self.preview_data['model_name']}_{Path(self.preview_data['model_path']).parent.name}.html"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Preview Report",
            default_filename,
            "HTML Files (*.html);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Ensure .html extension
        if not file_path.endswith('.html'):
            file_path += '.html'
        
        # Export
        success = export_preview_report(self.preview_data, file_path)
        
        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Preview report exported successfully!\n\nLocation: {file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                "Failed to export preview report. Check logs for details."
            )
        
    def approve_changes(self):
        """User approved changes"""
        reply = QMessageBox.question(
            self,
            "Confirm Migration",
            f"Are you sure you want to apply these changes?\n\n"
            f"• {self.preview_data['summary']['total_files']} files will be modified\n"
            f"• {self.preview_data['summary']['total_lines_changed']} lines will change\n"
            f"• Backup will be created automatically\n\n"
            "This action will modify TMDL files. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.user_approved = True
            self.accept()
