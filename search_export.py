"""
PSA Search & Export System
Full-text search + export to PDF, Markdown, TXT
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QWidget, QFileDialog,
    QComboBox, QCheckBox, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
# Add this after all imports
def get_theme(parent):
    """Get theme from parent window"""
    if hasattr(parent, 'theme'):
        return parent.theme
    # Fallback dark theme
    return {
        "bg_primary": "#1a2b2a",
        "bg_secondary": "#243535",
        "bg_tertiary": "#2d4444",
        "text_primary": "#f5f5f0",
        "text_secondary": "#b8b5ad",
        "accent_warm": "#d4a574",
        "accent_green": "#6b9e8a",
        "border": "#3a5555",
    }

# ===========================================================================
#   CONVERSATION SEARCH DIALOG
# ===========================================================================

class ConversationSearchDialog(QDialog):
    """Full-text search across all conversations"""
    
    conversation_selected = pyqtSignal(str)  # Emits conv_id
    
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.theme = get_theme(parent)
        self.setWindowTitle("Search Conversations")
        self.setMinimumSize(700, 600)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        title = QLabel("🔍 Search Conversations")
        title.setFont(QFont("Segoe UI", 18, weight=700))
        title.setStyleSheet(f"color: {self.theme['accent_warm']};")
        layout.addWidget(title)
        
        # Search box
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search messages, topics, or content...")
        self.search_input.setFont(QFont("Segoe UI", 11))
        self.search_input.textChanged.connect(self._perform_search)
        self.search_input.returnPressed.connect(self._open_selected)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 2px solid {self.theme['border']};
                border-radius: 8px;
                padding: 12px 16px;
            }}
            QLineEdit:focus {{
                border-color: {self.theme['accent_warm']};
            }}
        """)
        search_layout.addWidget(self.search_input, 1)
        
        # Search button
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self._perform_search)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        # Date filter
        self.date_filter = QComboBox()
        self.date_filter.addItems([
            "All time", "Today", "This week", "This month", "This year"
        ])
        self.date_filter.currentTextChanged.connect(self._perform_search)
        self.date_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.date_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Results count
        self.results_label = QLabel("0 results")
        self.results_label.setStyleSheet(f"color: {self.theme['text_secondary']};")
        layout.addWidget(self.results_label)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._open_selected)
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.theme['bg_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 12px;
                border-radius: 6px;
                margin: 4px 0;
            }}
            QListWidget::item:selected {{
                background-color: {self.theme['accent_green']};
            }}
            QListWidget::item:hover {{
                background-color: {self.theme['bg_tertiary']};
            }}
        """)
        layout.addWidget(self.results_list, 1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        open_btn = QPushButton("Open Selected")
        open_btn.clicked.connect(self._open_selected)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_tertiary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 10px 20px;
            }}
        """)
        
        btn_layout.addWidget(open_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
    
    def _perform_search(self):
        """Search through all conversations"""
        query = self.search_input.text().strip().lower()
        self.results_list.clear()
        
        if not query:
            self.results_label.setText("0 results")
            return
        
        # Get all conversations
        conversations = self.bridge.get_all_conversations()
        results = []
        
        for conv_id, title in conversations:
            # Load conversation messages
            messages = self.bridge.load_conversation(conv_id)
            
            # Search in messages
            matches = []
            for msg in messages:
                if query in msg['content'].lower():
                    matches.append(msg['content'][:100])  # Preview
            
            if matches:
                results.append({
                    'conv_id': conv_id,
                    'title': title,
                    'matches': len(matches),
                    'preview': matches[0]
                })
        
        # Display results
        self.results_label.setText(f"{len(results)} result{'s' if len(results) != 1 else ''}")
        
        for result in results:
            item_text = f"💬 {result['title']}\n"
            item_text += f"   {result['matches']} match{'es' if result['matches'] != 1 else ''}: {result['preview']}..."
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, result['conv_id'])
            self.results_list.addItem(item)
    
    def _open_selected(self):
        """Open the selected conversation"""
        current = self.results_list.currentItem()
        if current:
            conv_id = current.data(Qt.ItemDataRole.UserRole)
            self.conversation_selected.emit(conv_id)
            self.accept()
    
    def showEvent(self, event):
        """Focus search input when shown"""
        super().showEvent(event)
        self.search_input.setFocus()


# ===========================================================================
#   EXPORT DIALOG
# ===========================================================================

class ExportDialog(QDialog):
    """Export conversation to various formats"""
    
    def __init__(self, bridge, conv_id: str, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.conv_id = conv_id
        self.theme = get_theme(parent)
        self.setWindowTitle("Export Conversation")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        title = QLabel("📤 Export Conversation")
        title.setFont(QFont("Segoe UI", 18, weight=700))
        title.setStyleSheet(f"color: {self.theme['accent_warm']};")
        layout.addWidget(title)
        
        # Format selection
        format_label = QLabel("Export Format:")
        format_label.setFont(QFont("Segoe UI", 11, weight=600))
        layout.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "📄 Markdown (.md)",
            "📝 Plain Text (.txt)",
            "📋 HTML (.html)",
            "📊 JSON (.json)"
        ])
        self.format_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: 11pt;
            }}
        """)
        layout.addWidget(self.format_combo)
        
        # Options
        options_label = QLabel("Options:")
        options_label.setFont(QFont("Segoe UI", 11, weight=600))
        layout.addWidget(options_label)
        
        self.include_timestamps = QCheckBox("Include timestamps")
        self.include_timestamps.setChecked(True)
        self.include_timestamps.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(self.include_timestamps)
        
        self.include_system = QCheckBox("Include system messages")
        self.include_system.setChecked(False)
        self.include_system.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(self.include_system)
        
        layout.addStretch()
        
        # Preview
        preview_label = QLabel("Preview:")
        preview_label.setFont(QFont("Segoe UI", 11, weight=600))
        layout.addWidget(preview_label)
        
        self.preview_text = QLabel()
        self.preview_text.setWordWrap(True)
        self.preview_text.setStyleSheet(f"""
            QLabel {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        self._update_preview()
        layout.addWidget(self.preview_text)
        
        self.format_combo.currentTextChanged.connect(self._update_preview)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self._export)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_tertiary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 12px 24px;
            }}
        """)
        
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
    
    def _update_preview(self):
        """Update export preview"""
        messages = self.bridge.load_conversation(self.conv_id)
        
        if not messages:
            self.preview_text.setText("No messages to export")
            return
        
        preview = f"Conversation with {len(messages)} messages\n"
        preview += f"Format: {self.format_combo.currentText()}\n"
        
        if self.include_timestamps.isChecked():
            preview += "Includes: Timestamps ✓"
        
        self.preview_text.setText(preview)
    
    def _export(self):
        """Export the conversation"""
        format_text = self.format_combo.currentText()
        
        # Determine file extension
        if "Markdown" in format_text:
            ext = ".md"
            format_name = "Markdown"
        elif "Plain Text" in format_text:
            ext = ".txt"
            format_name = "Text"
        elif "HTML" in format_text:
            ext = ".html"
            format_name = "HTML"
        else:
            ext = ".json"
            format_name = "JSON"
        
        # Get save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Conversation",
            f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}",
            f"{format_name} Files (*{ext});;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        # Export
        try:
            messages = self.bridge.load_conversation(self.conv_id)
            content = self._format_export(messages, format_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Conversation exported to:\n{file_path}"
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export conversation:\n{e}"
            )
    
    def _format_export(self, messages: List[Dict], format_name: str) -> str:
        """Format messages for export"""
        
        if format_name == "Markdown":
            return self._format_markdown(messages)
        elif format_name == "Text":
            return self._format_text(messages)
        elif format_name == "HTML":
            return self._format_html(messages)
        else:  # JSON
            import json
            return json.dumps(messages, indent=2)
    
    def _format_markdown(self, messages: List[Dict]) -> str:
        """Format as Markdown"""
        output = f"# PSA Conversation\n\n"
        output += f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        output += "---\n\n"
        
        for msg in messages:
            role = "**You:**" if msg['role'] == 'user' else "**PSA:**"
            
            if self.include_timestamps.isChecked():
                output += f"{role} *{msg.get('ts', '')}*\n\n"
            else:
                output += f"{role}\n\n"
            
            output += f"{msg['content']}\n\n"
            output += "---\n\n"
        
        return output
    
    def _format_text(self, messages: List[Dict]) -> str:
        """Format as plain text"""
        output = f"PSA Conversation\n"
        output += f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += "="*70 + "\n\n"
        
        for msg in messages:
            role = "You:" if msg['role'] == 'user' else "PSA:"
            
            if self.include_timestamps.isChecked():
                output += f"{role} [{msg.get('ts', '')}]\n"
            else:
                output += f"{role}\n"
            
            output += f"{msg['content']}\n"
            output += "-"*70 + "\n\n"
        
        return output
    
    def _format_html(self, messages: List[Dict]) -> str:
        """Format as HTML"""
        output = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PSA Conversation</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { margin: 20px 0; padding: 15px; border-radius: 8px; }
        .user { background-color: #e3f2fd; }
        .assistant { background-color: #f1f8e9; }
        .role { font-weight: bold; margin-bottom: 8px; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>PSA Conversation</h1>
    <p><em>Exported: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</em></p>
    <hr>
"""
        
        for msg in messages:
            role_class = "user" if msg['role'] == 'user' else "assistant"
            role_name = "You" if msg['role'] == 'user' else "PSA"
            
            output += f"""
    <div class="message {role_class}">
        <div class="role">{role_name}"""
            
            if self.include_timestamps.isChecked():
                output += f""" <span class="timestamp">{msg.get('ts', '')}</span>"""
            
            output += f"""</div>
        <div class="content">{msg['content'].replace('\n', '<br>')}</div>
    </div>
"""
        
        output += """
</body>
</html>"""
        
        return output

