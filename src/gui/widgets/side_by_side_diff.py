"""
Side-by-Side Diff Viewer (ALM Toolkit style)
Shows before/after comparison with synchronized scrolling
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QSplitter, QScrollBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from typing import List
import difflib


class SideBySideTextEdit(QTextEdit):
    """Custom TextEdit with line numbers and synchronized scrolling"""
    
    def __init__(self, parent=None, is_left=True):
        super().__init__(parent)
        self.is_left = is_left
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # Hide vertical scrollbar - we'll use a shared one, but keep horizontal scrollbar
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Set tab width to 4 spaces
        self.setTabStopDistance(40)  # 4 characters * 10 pixels per char
        
    def set_content_with_highlights(self, lines: List[tuple], line_numbers: List):
        """Set content with line-by-line highlighting
        lines: List of (line_text, line_type) where line_type is 'added', 'removed', 'unchanged', or 'empty'
        line_numbers: List of line numbers to display
        """
        self.clear()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        for i, (line_text, line_type) in enumerate(lines):
            # Line number
            line_num = str(line_numbers[i]) if i < len(line_numbers) and line_numbers[i] != "" else ""
            line_num_text = f"{line_num:>4} "
            
            # Insert line number (gray)
            num_format = QTextCharFormat()
            num_format.setForeground(QColor("#858585"))
            cursor.insertText(line_num_text, num_format)
            
            # Insert line content with appropriate background
            content_format = QTextCharFormat()
            if line_type == 'added':
                content_format.setBackground(QColor("#d4ffd4"))
                content_format.setForeground(QColor("#006400"))
            elif line_type == 'removed':
                content_format.setBackground(QColor("#ffd4d4"))
                content_format.setForeground(QColor("#DC143C"))
            elif line_type == 'empty':
                pass  # Use default background
            else:  # unchanged
                pass  # Use default background and foreground
            
            cursor.insertText(line_text + "\n", content_format)
        
        # Move cursor to start
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)


class SideBySideDiffViewer(QWidget):
    """Side-by-side diff viewer with synchronized scrolling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top section: Side-by-side panels with vertical scrollbar
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left panel (Source/Old)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Left header
        left_header = QLabel("Current (Before Migration)")
        left_header.setStyleSheet("""
            color: #DC143C;
            padding: 8px;
            font-weight: bold;
            font-size: 12px;
            border-bottom: 1px solid #3a3a3a;
        """)
        left_layout.addWidget(left_header)
        
        self.left_text = SideBySideTextEdit(is_left=True)
        left_layout.addWidget(self.left_text)
        
        # Right panel (Target/New)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Right header
        right_header = QLabel("After Migration (New)")
        right_header.setStyleSheet("""
            color: #28a745;
            padding: 8px;
            font-weight: bold;
            font-size: 12px;
            border-bottom: 1px solid #3a3a3a;
        """)
        right_layout.addWidget(right_header)
        
        self.right_text = SideBySideTextEdit(is_left=False)
        right_layout.addWidget(self.right_text)
        
        # Add panels to splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        top_layout.addWidget(splitter)
        
        # Vertical scrollbar
        self.v_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        top_layout.addWidget(self.v_scrollbar)
        
        main_layout.addWidget(top_widget)
        
        # Connect synchronized scrolling
        self.v_scrollbar.valueChanged.connect(self.sync_vertical_scroll)
        
        # Connect text edit scrollbars to update shared vertical scrollbar
        self.left_text.verticalScrollBar().valueChanged.connect(self.on_text_vertical_scroll)
        self.right_text.verticalScrollBar().valueChanged.connect(self.on_text_vertical_scroll)
        
        # Connect horizontal scrollbars for sync (each editor has its own)
        self.left_text.horizontalScrollBar().valueChanged.connect(self.sync_horizontal_from_left)
        self.right_text.horizontalScrollBar().valueChanged.connect(self.sync_horizontal_from_right)
        
    def sync_vertical_scroll(self, value):
        """Synchronize vertical scrolling between both text edits"""
        # Block signals to prevent infinite loop
        self.left_text.verticalScrollBar().blockSignals(True)
        self.right_text.verticalScrollBar().blockSignals(True)
        
        # Set the scrollbar values AND scroll the content
        left_sb = self.left_text.verticalScrollBar()
        right_sb = self.right_text.verticalScrollBar()
        
        left_sb.setValue(value)
        right_sb.setValue(value)
        
        # Force the viewport to update with new scroll position
        self.left_text.viewport().update()
        self.right_text.viewport().update()
        
        self.left_text.verticalScrollBar().blockSignals(False)
        self.right_text.verticalScrollBar().blockSignals(False)
    
    def sync_horizontal_from_left(self, value):
        """Sync right horizontal scrollbar when left is scrolled"""
        right_sb = self.right_text.horizontalScrollBar()
        if right_sb.value() != value:
            right_sb.blockSignals(True)
            right_sb.setValue(value)
            # Force the viewport to update
            self.right_text.viewport().update()
            right_sb.blockSignals(False)
    
    def sync_horizontal_from_right(self, value):
        """Sync left horizontal scrollbar when right is scrolled"""
        left_sb = self.left_text.horizontalScrollBar()
        if left_sb.value() != value:
            left_sb.blockSignals(True)
            left_sb.setValue(value)
            # Force the viewport to update
            self.left_text.viewport().update()
            left_sb.blockSignals(False)
    
    def on_text_vertical_scroll(self, value):
        """Update shared vertical scrollbar when text edit is scrolled"""
        if self.v_scrollbar.value() != value:
            self.v_scrollbar.blockSignals(True)
            self.v_scrollbar.setValue(value)
            self.v_scrollbar.blockSignals(False)
            
            # Also sync the other text edit
            sender = self.sender()
            if sender == self.left_text.verticalScrollBar():
                if self.right_text.verticalScrollBar().value() != value:
                    self.right_text.verticalScrollBar().setValue(value)
            elif sender == self.right_text.verticalScrollBar():
                if self.left_text.verticalScrollBar().value() != value:
                    self.left_text.verticalScrollBar().setValue(value)
        
    def set_diff(self, old_content: str, new_content: str):
        """Set the diff content for side-by-side comparison"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        # Use difflib to compute differences
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        left_display = []  # (text, type)
        left_line_nums = []
        right_display = []
        right_line_nums = []
        
        left_line = 1
        right_line = 1
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i in range(i1, i2):
                    left_display.append((old_lines[i], 'unchanged'))
                    left_line_nums.append(left_line)
                    right_display.append((new_lines[j1 + (i - i1)], 'unchanged'))
                    right_line_nums.append(right_line)
                    left_line += 1
                    right_line += 1
                    
            elif tag == 'delete':
                for i in range(i1, i2):
                    left_display.append((old_lines[i], 'removed'))
                    left_line_nums.append(left_line)
                    right_display.append(("", 'empty'))
                    right_line_nums.append("")
                    left_line += 1
                    
            elif tag == 'insert':
                for j in range(j1, j2):
                    left_display.append(("", 'empty'))
                    left_line_nums.append("")
                    right_display.append((new_lines[j], 'added'))
                    right_line_nums.append(right_line)
                    right_line += 1
                    
            elif tag == 'replace':
                max_lines = max(i2 - i1, j2 - j1)
                for k in range(max_lines):
                    # Left side (removed)
                    if k < (i2 - i1):
                        left_display.append((old_lines[i1 + k], 'removed'))
                        left_line_nums.append(left_line)
                        left_line += 1
                    else:
                        left_display.append(("", 'empty'))
                        left_line_nums.append("")
                    
                    # Right side (added)
                    if k < (j2 - j1):
                        right_display.append((new_lines[j1 + k], 'added'))
                        right_line_nums.append(right_line)
                        right_line += 1
                    else:
                        right_display.append(("", 'empty'))
                        right_line_nums.append("")
        
        # Set content
        self.left_text.set_content_with_highlights(left_display, left_line_nums)
        self.right_text.set_content_with_highlights(right_display, right_line_nums)
        
        # Setup vertical scrollbar to match the text edit scrollbars
        left_v_scrollbar = self.left_text.verticalScrollBar()
        right_v_scrollbar = self.right_text.verticalScrollBar()
        
        max_v_value = max(left_v_scrollbar.maximum(), right_v_scrollbar.maximum())
        self.v_scrollbar.setMinimum(0)
        self.v_scrollbar.setMaximum(max_v_value)
        self.v_scrollbar.setPageStep(left_v_scrollbar.pageStep())
        self.v_scrollbar.setSingleStep(1)
        
        # Update scrollbars when content scrolls
        left_v_scrollbar.rangeChanged.connect(self.update_scrollbar_range)
        right_v_scrollbar.rangeChanged.connect(self.update_scrollbar_range)
    
    def update_scrollbar_range(self):
        """Update scrollbar range when text content changes"""
        # Update vertical scrollbar
        left_v_max = self.left_text.verticalScrollBar().maximum()
        right_v_max = self.right_text.verticalScrollBar().maximum()
        max_v_value = max(left_v_max, right_v_max)
        self.v_scrollbar.setMaximum(max_v_value)
        self.v_scrollbar.setPageStep(self.left_text.verticalScrollBar().pageStep())


