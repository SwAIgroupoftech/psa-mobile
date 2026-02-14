"""
Simple Classic Settings Dialog for PSA
Clean, straightforward settings without unnecessary complexity
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import webbrowser


def get_theme(parent):
    """Get theme from parent"""
    if hasattr(parent, 'theme'):
        return parent.theme
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


class SettingsDialog(QDialog):
    """Simple settings dialog"""
    
    theme_changed = pyqtSignal()
    
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.theme = get_theme(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setFont(QFont("Segoe UI", 18, weight=700))
        title.setStyleSheet(f"color: {self.theme['accent_warm']};")
        layout.addWidget(title)
        
        # Appearance
        appearance_group = QGroupBox("Appearance")
        appearance_group.setStyleSheet(f"""
            QGroupBox {{
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
        """)
        appearance_layout = QVBoxLayout()
        
        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        appearance_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Theme", "Light Theme"])
        # Set current theme
        try:
            from main import theme_manager
            current = 0 if theme_manager.is_dark() else 1
            self.theme_combo.setCurrentIndex(current)
        except:
            pass
        
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                selection-background-color: {self.theme['accent_green']};
            }}
        """)
        appearance_layout.addWidget(self.theme_combo)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        
        # Support
        support_group = QGroupBox("Support & Feedback")
        support_group.setStyleSheet(f"""
            QGroupBox {{
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
        """)
        support_layout = QVBoxLayout()
        
        feedback_btn = QPushButton("📧 Send Feedback")
        feedback_btn.clicked.connect(self.show_feedback)
        
        feedback_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        support_layout.addWidget(feedback_btn)
        
        about_btn = QPushButton("ℹ️ About PSA")
        about_btn.clicked.connect(self._show_about)
        about_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_warm']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_green']};
            }}
        """)
        support_layout.addWidget(about_btn)
        
        support_group.setLayout(support_layout)
        layout.addWidget(support_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
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
                border-radius: 6px;
                padding: 10px 24px;
            }}
        """)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
    
    def _save_settings(self):
        """Save settings"""
        # Check theme change
        new_theme = self.theme_combo.currentIndex()
        try:
            from main import theme_manager
            current_is_dark = theme_manager.is_dark()
            should_be_dark = (new_theme == 0)
            
            if current_is_dark != should_be_dark:
                theme_manager.toggle_theme()
                self.theme_changed.emit()
        except:
            pass
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved!")
        self.accept()

    def show_feedback(self):
        feedback_text = "Mail us at <b>nandngroupoftech@gmail.com<b>"
        msg = QMessageBox(self)
        msg.setWindowTitle("About PSA")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(feedback_text)
        msg.exec()
        
        
    def _show_about(self):
        """Show about dialog"""
        about_text = """
<h2>PSA - Personal Smart Assistant</h2>
<p><b>Version:</b> 1.0.0</p>
<p><b>Created by:</b> Nachiketh (SwAI)</p>

<h3>Features</h3>
<ul>
<li>🧠 Automatic memory learning</li>
<li>🔍 Web search integration</li>
<li>📸 Image analysis</li>
<li>🎤 Voice input</li>
<li>💾 Conversation export</li>
<li>📌 Pin & favorite chats</li>
<li>🔒 Encrypted storage</li>
</ul>

<p><i>"AI that learns you without being told."</i></p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About PSA")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.exec()

    