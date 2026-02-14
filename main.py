
import sys
import webbrowser
import urllib.parse
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit, QTextEdit, QFrame,
    QListWidget, QListWidgetItem, QMessageBox, QStackedWidget,
    QInputDialog, QDialog, QDialogButtonBox, QGroupBox, QSplitter,
    QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEvent, QSettings, QTimer,QSize
from PyQt6.QtGui import QFont, QCursor, QTextCursor
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QPushButton, QFileDialog, QLabel, QFrame,
    QHBoxLayout, QVBoxLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from pathlib import Path

from bridge import PSABackendBridge, StreamingThread
from core import start_reminder_service
from conversations import get_conversation,add_message
# Add these to your existing imports at the top
import sys
import webbrowser
import urllib.parse
from datetime import datetime
from pathlib import Path
from PyQt6.QtGui import QFont, QCursor, QTextCursor, QColor, QBrush

from search_export import (
    ConversationSearchDialog, ExportDialog
)

from pinning_system import (
    ConversationMetadata, ConversationListItem
)
from settings_dialog import SettingsDialog
from voice_input import quick_voice_input
# ===========================================================================
#   MARKDOWN RENDERING
# ============================================================================

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# Global CSS for markdown rendering
_GLOBAL_CSS = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
    padding: 8px;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 16px;
    margin-bottom: 8px;
    font-weight: 600;
    color: #2c3e50;
}

h1 { font-size: 20pt; }
h2 { font-size: 18pt; }
h3 { font-size: 16pt; }
h4 { font-size: 14pt; }

p {
    margin: 8px 0;
}

code {
    background-color: #f4f4f4;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10pt;
    color: #c7254e;
}

pre {
    background-color: #2d2d2d;
    color: #f8f8f2;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 12px 0;
}

pre code {
    background-color: transparent;
    padding: 0;
    color: #f8f8f2;
    font-size: 10pt;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    background-color: white;
}

th {
    background-color: #6b9e8a;
    color: white;
    padding: 10px;
    text-align: left;
    font-weight: 600;
    border: 1px solid #5a8a76;
}

td {
    padding: 10px;
    border: 1px solid #ddd;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

tr:hover {
    background-color: #f0f0f0;
}

ul, ol {
    margin: 8px 0;
    padding-left: 24px;
}

li {
    margin: 4px 0;
}

blockquote {
    border-left: 4px solid #6b9e8a;
    padding-left: 12px;
    margin: 12px 0;
    color: #666;
    font-style: italic;
}

a {
    color: #6b9e8a;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

strong {
    font-weight: 600;
    color: #2c3e50;
}

em {
    font-style: italic;
}

hr {
    border: none;
    border-top: 2px solid #ddd;
    margin: 16px 0;
}
"""

def render_markdown(text: str) -> str:
    """
    Convert markdown string to a complete styled HTML document.
    Returns formatted HTML ready for QTextBrowser/QLabel display.
    """
    if not MARKDOWN_AVAILABLE:
        # Fallback if markdown not installed
        return text.replace('\n', '<br>')
    
    # Convert markdown to HTML body
    body = markdown.markdown(
        text,
        extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists', 'codehilite'],
        extension_configs={
            'codehilite': {
                'noclasses': True,
                'guess_lang': True,
                'pygments_style': 'monokai'
            }
        }
    )
    
    # Return complete HTML document with styling
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>{_GLOBAL_CSS}</style>
</head>
<body>{body}</body>
</html>"""
# ============================================================================
#   USER ANALYTICS (Anonymous)
# ============================================================================

import requests
import threading
from datetime import datetime

# PostHog Configuration
POSTHOG_API_KEY = "phc_v8tW9k8Aw5xWsZv2caam5OxsN6YvYlOeZJOOWfDSi3J"  # â† PASTE YOUR KEY HERE
POSTHOG_HOST = "https://app.posthog.com"

def track_signup_anonymous():
    """Send anonymous ping when new user signs up"""
    def send_ping():
        try:
            requests.post(
                f"{POSTHOG_HOST}/capture/",
                json={
                    "api_key": POSTHOG_API_KEY,
                    "event": "user_signup",
                    "properties": {
                        "distinct_id": f"user_{datetime.now().timestamp()}",
                        "$lib": "psa-desktop",
                        "version": "1.0.0"
                    },
                    "timestamp": datetime.now().isoformat()
                },
                timeout=3
            )
        except:
            pass  # Silently fail - don't break app if analytics fails
    
    # Send in background thread
    thread = threading.Thread(target=send_ping, daemon=True)
    thread.start()
def track_event(event_name: str, properties: dict = None):
    """Generic event tracking"""
    def send_event():
        try:
            event_data = {
                "api_key": POSTHOG_API_KEY,
                "event": event_name,
                "properties": {
                    "distinct_id": f"user_{datetime.now().timestamp()}",
                    "$lib": "psa-desktop",
                    "version": "1.0.0"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Add custom properties
            if properties:
                event_data["properties"].update(properties)
            
            requests.post(
                f"{POSTHOG_HOST}/capture/",
                json=event_data,
                timeout=3
            )
        except:
            pass
    
    threading.Thread(target=send_event, daemon=True).start()

def track_login():
    """Track user login"""
    track_event("user_login")

def track_message_sent():
    """Track when user sends a message"""
    track_event("message_sent")

def track_memory_added(category: str):
    """Track when memory is automatically detected"""
    track_event("memory_added", {"category": category})
# ============================================================================
#   THEME SYSTEM
# ============================================================================

DARK_THEME = {
    "bg_primary": "#1a2b2a",
    "bg_secondary": "#243535",
    "bg_tertiary": "#2d4444",
    "text_primary": "#f5f5f0",
    "text_secondary": "#b8b5ad",
    "accent_warm": "#d4a574",
    "accent_green": "#6b9e8a",
    "user_msg": "#c5e4f3",
    "asst_msg": "#c8e6c9",
    "border": "#3a5555",
}

LIGHT_THEME = {
    "bg_primary": "#f5f5f0",
    "bg_secondary": "#e8e8e0",
    "bg_tertiary": "#d8d8d0",
    "text_primary": "#1a1a1a",
    "text_secondary": "#4a4a4a",
    "accent_warm": "#d4a574",
    "accent_green": "#6b9e8a",
    "user_msg": "#b3d9ff",
    "asst_msg": "#b3e6b3",
    "border": "#c0c0c0",
}
class FileUploadWidget(QFrame):
    """Drag-and-drop file upload widget"""
    
    file_selected = pyqtSignal(str)  # Emits file path when file is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = theme_manager.get_theme()
        self.setAcceptDrops(True)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Drop zone label
        self.drop_label = QLabel("📎 Drag & drop files here\nor click to browse")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setWordWrap(True)
        self.drop_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_secondary']};
                border: 2px dashed {self.theme['border']};
                border-radius: 8px;
                padding: 20px;
                font-size: 11pt;
            }}
        """)
        self.drop_label.setMinimumHeight(80)
        self.drop_label.mousePressEvent = lambda e: self._browse_files()
        layout.addWidget(self.drop_label)
        
        # Browse button
        browse_btn = QPushButton("📁 Browse Files")
        browse_btn.clicked.connect(self._browse_files)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        layout.addWidget(browse_btn)
        
        # Supported formats label
        formats_label = QLabel(
            "Supported: Images (jpg, png), Documents (pdf, docx, txt, md)"
        )
        formats_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: 9pt;")
        formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(formats_label)
        
        self.setLayout(layout)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.theme['accent_green']};
                    color: {self.theme['text_primary']};
                    border: 2px dashed {self.theme['accent_warm']};
                    border-radius: 8px;
                    padding: 20px;
                    font-size: 11pt;
                }}
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self.drop_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_secondary']};
                border: 2px dashed {self.theme['border']};
                border-radius: 8px;
                padding: 20px;
                font-size: 11pt;
            }}
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.file_selected.emit(files[0])  # Process first file
        
        # Reset style
        self.dragLeaveEvent(None)
    
    def _browse_files(self):
        """Open file browser dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "All Supported Files (*.jpg *.jpeg *.png *.gif *.pdf *.docx *.txt *.md);;Images (*.jpg *.jpeg *.png *.gif);;Documents (*.pdf *.docx *.txt *.md);;All Files (*.*)"
        )
        
        if file_path:
            self.file_selected.emit(file_path)

class FilePreviewWidget(QFrame):
    """Show preview of selected file"""
    
    remove_requested = pyqtSignal()
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.theme = theme_manager.get_theme()
        self.file_path = file_path
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # File type icon and name
        file_name = Path(self.file_path).name
        file_ext = Path(self.file_path).suffix.lower()
        
        # Icon based on type
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            icon = "🖼️"
        elif file_ext == '.pdf':
            icon = "📄"
        elif file_ext in ['.docx', '.doc']:
            icon = "📝"
        else:
            icon = "📎"
        
        file_label = QLabel(f"{icon} {file_name}")
        file_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(file_label, 1)
        
        # Remove button
        remove_btn = QPushButton("✖")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setToolTip("Remove file")
        remove_btn.clicked.connect(self.remove_requested.emit)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_tertiary']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: #ff4444;
            }}
        """)
        layout.addWidget(remove_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
            }}
        """)
class ThemeManager:
    """Manages application theme"""
    def __init__(self):
        self.settings = QSettings("PSA", "PersonalSmartAssistant")
        self._current_theme = self.settings.value("theme", "dark")
    
    def get_theme(self):
        return DARK_THEME if self._current_theme == "dark" else LIGHT_THEME
    
    def toggle_theme(self):
        self._current_theme = "light" if self._current_theme == "dark" else "dark"
        self.settings.setValue("theme", self._current_theme)
        return self.get_theme()
    
    def is_dark(self):
        return self._current_theme == "dark"

theme_manager = ThemeManager()

# ============================================================================
#   ONBOARDING DIALOG
# ============================================================================

class OnboardingDialog(QDialog):
    """First-time user onboarding"""
    
    def __init__(self, bridge: PSABackendBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.theme = theme_manager.get_theme()
        self.setWindowTitle("Welcome to PSA!")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.current_step = 0
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Stacked widget for steps
        self.stack = QStackedWidget()
        
        # Step 1: Welcome
        step1 = self._create_step1()
        self.stack.addWidget(step1)
        
        # Step 2: Memory explanation
        step2 = self._create_step2()
        self.stack.addWidget(step2)
        
        # Step 3: Add memory items
        step3 = self._create_step3()
        self.stack.addWidget(step3)
        
        # Step 4: Reminders
        step4 = self._create_step4()
        self.stack.addWidget(step4)
        
        # Step 5: Done
        step5 = self._create_step5()
        self.stack.addWidget(step5)
        
        layout.addWidget(self.stack)
        
        # Navigation buttons
        btn_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._prev_step)
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._next_step)
        
        btn_layout.addWidget(self.back_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.next_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self._update_buttons()
        self._apply_theme()
    
    def _create_step1(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("👋 Welcome to PSA!")
        title.setFont(QFont("Segoe UI", 24, weight=700))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        text = QLabel(
            "PSA is different from Other AI Assistants.\n\n"
            "It learns about you automatically from conversations\n"
            "and remembers across sessions.\n\n"
            "Let's take a quick tour!"
        )
        text.setFont(QFont("Segoe UI", 12))
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        layout.addWidget(text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_step2(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Automatic Memory")
        title.setFont(QFont("Segoe UI", 20, weight=700))
        layout.addWidget(title)
        
        text = QLabel(
            "PSA automatically detects and remembers:\n\n"
            "• Your name when you mention it\n"
            "• Things you like: 'I love cricket'\n"
            "• Things you dislike: 'I hate frogs'\n"
            "• Your goals: 'I want to learn Python'\n"
            "• Your hobbies: 'I enjoy gaming'\n"
            "• Important facts: 'Remember I'm vegetarian'\n\n"
            "No need to say 'remember this' - PSA just learns!"
        )
        text.setFont(QFont("Segoe UI", 11))
        text.setWordWrap(True)
        layout.addWidget(text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_step3(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel(" Let's Add Some Memories")
        title.setFont(QFont("Segoe UI", 20, weight=700))
        layout.addWidget(title)
        
        text = QLabel("Tell PSA a bit about yourself to get started:")
        text.setFont(QFont("Segoe UI", 11))
        layout.addWidget(text)
        
        # Name
        name_label = QLabel("Your name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Nachiketh")
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        
        # Likes
        likes_label = QLabel("Something you like:")
        self.likes_input = QLineEdit()
        self.likes_input.setPlaceholderText("e.g., cricket, coding, music")
        layout.addWidget(likes_label)
        layout.addWidget(self.likes_input)
        
        # Goals
        goals_label = QLabel("A goal you have:")
        self.goals_input = QLineEdit()
        self.goals_input.setPlaceholderText("e.g., learn Python, get fit")
        layout.addWidget(goals_label)
        layout.addWidget(self.goals_input)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_step4(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel(" Smart Reminders")
        title.setFont(QFont("Segoe UI", 20, weight=700))
        layout.addWidget(title)
        
        text = QLabel(
            "Set reminders in natural language:\n\n"
        "Just type:\n"
        "'remind on 27/12/24 at 6:30 PM to study Tamil'\n\n"
        " Note: Reminders are being improved and will be fully functional in the next version.\n"
        "For now, focus on the automatic memory feature!"
        )
        text.setFont(QFont("Segoe UI", 11))
        text.setWordWrap(True)
        layout.addWidget(text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_step5(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("🎉 You're All Set!")
        title.setFont(QFont("Segoe UI", 24, weight=700))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        text = QLabel(
            "Key things to remember:\n\n"
            "• Chat naturally - PSA learns automatically\n"
            "• Your memory panel (right side) shows what PSA knows\n"
            "• You can edit or delete memories anytime\n"
            "• Everything is stored locally and encrypted\n\n"
            "• Start chatting and PSA will get to know you!"
        )
        text.setFont(QFont("Segoe UI", 12))
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        layout.addWidget(text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _next_step(self):
        if self.current_step == 2:  # Step 3 - save memories
            self._save_onboarding_memories()
        
        if self.current_step < self.stack.count() - 1:
            self.current_step += 1
            self.stack.setCurrentIndex(self.current_step)
            self._update_buttons()
        else:
            self.accept()
    
    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self._update_buttons()
    
    def _update_buttons(self):
        self.back_btn.setEnabled(self.current_step > 0)
        if self.current_step == self.stack.count() - 1:
            self.next_btn.setText("Get Started!")
        else:
            self.next_btn.setText("Next")
    
    def _save_onboarding_memories(self):
        """Save memories from onboarding"""
        name = self.name_input.text().strip()
        likes = self.likes_input.text().strip()
        goals = self.goals_input.text().strip()
        
        if name:
            self.bridge.add_memory("name", name)
        if likes:
            self.bridge.add_memory("likes", likes)
        if goals:
            self.bridge.add_memory("goals", goals)
    
    def _apply_theme(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.theme['bg_primary']};
                color: {self.theme['text_primary']};
            }}
            QLabel {{
                color: {self.theme['text_primary']};
            }}
            QLineEdit {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 8px;
            }}
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
            QPushButton:disabled {{
                background-color: {self.theme['bg_tertiary']};
            }}
        """)

# ============================================================================
#   SETTINGS DIALOG
# ============================================================================


# ============================================================================
#   LOGIN SCREEN
# ============================================================================

class LoginScreen(QWidget):
    def __init__(self, bridge: PSABackendBridge, on_login_success):
        super().__init__()
        self.bridge = bridge
        self.on_login_success = on_login_success
        self.theme = theme_manager.get_theme()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 80, 60, 100)
        layout.setSpacing(20)
        
        
        layout.addSpacing(20)
        
        # Title
        title = QLabel("PSA")
        title.setFont(QFont("Segoe UI", 48, weight=700))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Personal Smart Assistant")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        tagline = QLabel("AI that learns you without being told")
        tagline.setFont(QFont("Segoe UI", 10, QFont.Weight.Light))
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)
        
        layout.addSpacing(40)
        
        # Username
        username_label = QLabel("Username")
        username_label.setFont(QFont("Segoe UI", 11, weight=600))
        username_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFont(QFont("Segoe UI", 11))
        self.username_input.setMinimumHeight(40)
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        password_label.setFont(QFont("Segoe UI", 11, weight=600))
        password_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(password_label)
        
        # Password with show/hide toggle
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFont(QFont("Segoe UI", 11))
        self.password_input.setMinimumHeight(40)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_input)
        
        self.show_password_btn = QPushButton("👁️")
        self.show_password_btn.setFixedSize(40, 40)
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.clicked.connect(self._toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)
        
        layout.addLayout(password_layout)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.login_btn = QPushButton("Login")
        self.login_btn.setFont(QFont("Segoe UI", 11, weight=600))
        self.login_btn.setMinimumHeight(44)
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.clicked.connect(self._on_login)
        button_layout.addWidget(self.login_btn, 1)
        
        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.setFont(QFont("Segoe UI", 11, weight=600))
        self.signup_btn.setMinimumHeight(44)
        self.signup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.signup_btn.clicked.connect(self._on_signup)
        button_layout.addWidget(self.signup_btn, 1)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        self._apply_theme()
    
    def _toggle_password_visibility(self):
        if self.show_password_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("👁️")
    
    def _apply_theme(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme['bg_primary']};
            }}
            QLineEdit {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 10px 15px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.theme['accent_warm']};
            }}
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
            QPushButton#theme_btn {{
                background-color: {self.theme['bg_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 20px;
            }}
        """)
        
        # Apply specific styles
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        
        self.signup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_warm']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_green']};
            }}
        """)
        
        
        self.show_password_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_tertiary']};
            }}
        """)
    
    
    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        ok, msg = self.bridge.authenticate(username, password)
        if ok:
            self.on_login_success()
        else:
            QMessageBox.warning(self, "Login Failed", msg)
    
    def _on_signup(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return
        
        ok, msg = self.bridge.authenticate(username, password, create_if_missing=True)
        if ok:
            # Track signup anonymously
            track_signup_anonymous()
            
            # Show onboarding
            self.on_login_success(show_onboarding=True)
        else:
            QMessageBox.warning(self, "Signup Failed", msg)

# ============================================================================
#   MESSAGE BUBBLE WITH MARKDOWN
# ============================================================================

class MessageBubble(QFrame):
    regenerate_requested = pyqtSignal(str)
    read_requested = pyqtSignal(str)
    
    def __init__(self, role: str, content: str, timestamp: str):
        super().__init__()
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.theme = theme_manager.get_theme()
        
        is_user = role == "user"
        bg = self.theme["user_msg"] if is_user else self.theme["asst_msg"]
        
        # Message label
        self.msg_label = QLabel()
        self.msg_label.setWordWrap(True)
        self.msg_label.setFont(QFont("Segoe UI", 11))
        self.msg_label.setTextFormat(Qt.TextFormat.RichText if not is_user else Qt.TextFormat.PlainText)
        self.msg_label.setOpenExternalLinks(True)
        
        if is_user:
            self.msg_label.setText(content)
        else:
            # Render markdown for assistant
            html_content = render_markdown(content)
            self.msg_label.setText(html_content)

        self.msg_label.setStyleSheet(f"""
            QLabel {{
                color: #1a1a1a;
                background-color: {bg};
                padding: 12px;
                border-radius: 12px;
            }}
        """)
        self.msg_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        
        # IMPORTANT: Set size policy to allow expansion
        from PyQt6.QtWidgets import QSizePolicy
        self.msg_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )

        # Create action buttons
        self.btns = []
        self.copy_btn = self._make_btn("📋", "Copy")
        self.btns.append(self.copy_btn)

        if not is_user:
            self.regen_btn = self._make_btn("🔄", "Regenerate")
            self.btns.append(self.regen_btn)
            self.regen_btn.clicked.connect(lambda: self.regenerate_requested.emit(self.content))

        self.read_btn = self._make_btn("🔊", "Read aloud")
        self.btns.append(self.read_btn)
        self.read_btn.clicked.connect(lambda: self.read_requested.emit(self.content))

        self.copy_btn.clicked.connect(self._copy)

        # Button container
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background: transparent;")
        btn_layout_h = QHBoxLayout()
        btn_layout_h.setContentsMargins(8, 2, 8, 2)
        btn_layout_h.setSpacing(4)

        if is_user:
            btn_layout_h.addStretch()
            for b in self.btns:
                btn_layout_h.addWidget(b)
                b.hide()
        else:
            for b in self.btns:
                btn_layout_h.addWidget(b)
                b.hide()
            btn_layout_h.addStretch()

        btn_widget.setLayout(btn_layout_h)
        btn_widget.setFixedHeight(32)
        self.btn_widget = btn_widget

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        if is_user:
            # User: message on right, buttons below
            msg_container = QHBoxLayout()
            msg_container.addStretch(1)
            msg_container.addWidget(self.msg_label, 3)  # Takes 75% of space
            layout.addLayout(msg_container)
            layout.addWidget(btn_widget)
        else:
            # Assistant: buttons above, message on left
            layout.addWidget(btn_widget)
            msg_container = QHBoxLayout()
            msg_container.addWidget(self.msg_label, 3)  # Takes 75% of space
            msg_container.addStretch(1)
            layout.addLayout(msg_container)

        self.setLayout(layout)
        self.setStyleSheet("QFrame { background-color: transparent; border: none; }")
    
    def _make_btn(self, icon, tooltip):
        """Create small button"""
        btn = QPushButton(icon)
        btn.setToolTip(tooltip)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                font-size: 12px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
                border: 1px solid {self.theme['accent_warm']};
            }}
        """)
        return btn
    
    def _copy(self):
        QApplication.clipboard().setText(self.content)
    
    def update_content(self, new_content: str):
        self.content = new_content
        if self.role == "assistant":
            html_content = render_markdown(new_content)
            self.msg_label.setText(html_content)
        else:
            self.msg_label.setText(new_content)
    
    def enterEvent(self, e):
        """Show buttons on hover"""
        for b in self.btns:
            b.show()

    def leaveEvent(self, e):
        """Hide buttons when not hovering"""
        for b in self.btns:
            b.hide()
# ============================================================================
#   MEMORY CARD
# ============================================================================

class MemoryCard(QFrame):
    delete_requested = pyqtSignal(str, str)
    edit_requested = pyqtSignal(str, str)
    
    def __init__(self, category: str, value: str):
        super().__init__()
        self.category = category
        self.value = value
        self.theme = theme_manager.get_theme()
        
        icons = {"name": "👤", "likes": "❤️", "dislikes": "👎", "hobbies": "🎮", "goals": "🎯", "facts": "ℹ️"}
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        content = QLabel(f"{icons.get(category, '📌')} {value}")
        content.setWordWrap(True)
        content.setFont(QFont("Segoe UI", 10))
        content.setStyleSheet(f"color: {self.theme['text_primary']};")
        
        layout.addWidget(content, 1)
        
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setToolTip("Edit")
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.hide()
        
        self.del_btn = QPushButton("🗑️")
        self.del_btn.setToolTip("Delete")
        self.del_btn.setFixedSize(28, 28)
        self.del_btn.hide()
        
        btn_style = f"""
            QPushButton {{
                background-color: {self.theme['bg_tertiary']};
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """
        self.edit_btn.setStyleSheet(btn_style)
        self.del_btn.setStyleSheet(btn_style)
        
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.category, self.value))
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.category, self.value))
        
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.del_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
    
    def enterEvent(self, e):
        self.edit_btn.show()
        self.del_btn.show()
    
    def leaveEvent(self, e):
        self.edit_btn.hide()
        self.del_btn.hide()

# ============================================================================
#   COLLAPSIBLE PANEL
# ============================================================================

class CollapsiblePanel(QWidget):
    """Collapsible sidebar panel"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.theme = theme_manager.get_theme()
        self.is_collapsed = False
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 8, 8, 8)
        
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 11, weight=700))
        header_layout.addWidget(self.title_label)
        
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_btn)
        
        header.setLayout(header_layout)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                
            }}
        """)
        header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        header.mousePressEvent = lambda e: self.toggle()
        
        layout.addWidget(header)
        
        # Content
        self.content_widget = QWidget()
        layout.addWidget(self.content_widget)
        
        self.setLayout(layout)
    
    def set_content(self, widget):
        """Set the collapsible content"""
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.addWidget(widget)
        self.content_widget.setLayout(content_layout)
    
    def toggle(self):
        """Toggle collapsed state"""
        self.is_collapsed = not self.is_collapsed
        self.content_widget.setVisible(not self.is_collapsed)
        self.toggle_btn.setText("â–¶" if self.is_collapsed else "â–¼")

# ============================================================================
#   MAIN APPLICATION
# ============================================================================

class PSAMainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSA - Personal Smart Assistant")
        self.setGeometry(100, 100, 1600, 900)
        self.theme = theme_manager.get_theme()
        
        self.bridge = PSABackendBridge()
        self.conv_metadata = None  # Initialize after login
        self.showing_favorites_only = False
        self.loading_overlay = None
        self.typing_indicator = None
    
        self.stacked = QStackedWidget()
        self.login_screen = LoginScreen(self.bridge, self._on_login_success)
        self.stacked.addWidget(self.login_screen)
        self.current_file = None
        self.file_preview = None
        self.main_screen = None
        self.setCentralWidget(self.stacked)
        self.streaming_thread = None
        self.current_assistant_bubble = None
        
        self.stacked = QStackedWidget()
        self.login_screen = LoginScreen(self.bridge, self._on_login_success)
        self.stacked.addWidget(self.login_screen)
        self.current_file = None  # Track uploaded file
        self.file_preview = None  # Preview widget
        self.main_screen = None
        self.setCentralWidget(self.stacked)
    
    def _on_login_success(self, show_onboarding=False):
        if not self.main_screen:
            self.main_screen = self._create_main_screen()
            self.stacked.addWidget(self.main_screen)
        
        # NEW: Setup keyboard shortcuts after UI is created
            
    
        track_login()
        self.stacked.setCurrentWidget(self.main_screen)
    
    # NEW: Initialize conversation metadata
        self.conv_metadata = ConversationMetadata(self.bridge.username)
    
    # Use enhanced refresh with pinning
        self._refresh_conversations_with_pinning()
        self._refresh_memory()
        self._refresh_reminders()
    
    # Start reminder service
        if self.bridge.username:
            start_reminder_service(self.bridge.username)
    
        if self.bridge.current_conv_id is None:
            self._new_conversation()
    
    # Show onboarding for new users
        if show_onboarding:
            self._show_onboarding()
    
    def _show_onboarding(self):
        """Show onboarding dialog"""
        dialog = OnboardingDialog(self.bridge, self)
        dialog.exec()
        self._refresh_memory()  # Refresh after onboarding adds memories
    
    def _create_main_screen(self):
        main = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
    
        # Left sidebar
        left_sidebar = self._create_left_sidebar()
        layout.addWidget(left_sidebar, 0)  # Fixed width
    
        # Chat area
        chat = self._create_chat_area()
        layout.addWidget(chat, 1)  # Stretches
    
        # Right sidebar
        right_sidebar = self._create_right_sidebar()
        layout.addWidget(right_sidebar, 0)  # Fixed width
        
        main.setLayout(layout)
        return main
    
    def _create_left_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        self.left_sidebar = sidebar  # ADD THIS LINE
    
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
    
        # Header with collapse button
        header_layout = QHBoxLayout()
        title = QLabel("PSA")
        title.setFont(QFont("Segoe UI", 20, weight=700))
        title.setStyleSheet(f"color: {self.theme['accent_warm']};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        
    
        # Settings button (existing)
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {self.theme['bg_secondary']};
            border: 1px solid {self.theme['border']};
            border-radius: 16px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {self.theme['accent_warm']};
        }}
    """)
        settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(settings_btn)
        layout.addLayout(header_layout)
    
        # ... rest of your existing code ...
        
        # New Chat
        new_btn = QPushButton("+ New Chat")
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        new_btn.clicked.connect(self._new_conversation)
        layout.addWidget(new_btn)
        # Search conversations button (NEW!)
        search_conv_btn = QPushButton("🔍 Search Conversations")
        search_conv_btn.setStyleSheet(f"""
    QPushButton {{
        background-color: {self.theme['bg_secondary']};
        color: {self.theme['text_primary']};
        border: 1px solid {self.theme['border']};
        border-radius: 8px;
        padding: 10px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {self.theme['accent_warm']};
    }}
""")
        search_conv_btn.clicked.connect(self._search_conversations)
        layout.addWidget(search_conv_btn)

# Add small spacer
        layout.addSpacing(8)


        # Conversations panel (collapsible)
       # Conversations (direct list, no collapsible wrapper)
        conv_label = QLabel("Recent Chats")
        conv_label.setFont(QFont("Segoe UI", 11, weight=700))
        conv_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(conv_label)

        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(self._on_conversation_selected)
        self.conv_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.conv_list.customContextMenuRequested.connect(self._conversation_context_menu)
        self.conv_list.setStyleSheet(f"""
    QListWidget {{
        background-color: {self.theme['bg_secondary']};
        border: 1px solid {self.theme['border']};
        border-radius: 6px;
        color: {self.theme['text_primary']};
        padding: 4px;
        font-size: 11pt;
    }}
    QListWidget::item {{
        padding: 10px 8px;
        border-radius: 4px;
        color: {self.theme['text_primary']};
        background-color: transparent;
        min-height: 24px;
    }}
    QListWidget::item:selected {{
        background-color: {self.theme['accent_green']};
        color: {self.theme['text_primary']};
    }}
    QListWidget::item:hover {{
        background-color: {self.theme['bg_tertiary']};
        color: {self.theme['text_primary']};
    }}
""")
        layout.addWidget(self.conv_list)
        
        # Reminders (direct list, no collapsible wrapper)
        rem_label = QLabel("Upcoming Reminders")
        rem_label.setFont(QFont("Segoe UI", 11, weight=700))
        rem_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(rem_label)

        self.rem_list = QListWidget()
        self.rem_list.setStyleSheet(f"""
    QListWidget {{
        background-color: {self.theme['bg_secondary']};
        border: 1px solid {self.theme['border']};
        border-radius: 6px;
        color: {self.theme['text_primary']};
    }}
""")
        layout.addWidget(self.rem_list)
        
        # Logout
        logout_btn = QPushButton("🚪 Logout")
        
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        logout_btn.clicked.connect(self._logout)
        layout.addWidget(logout_btn)
        
        sidebar.setLayout(layout)
        sidebar.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
        return sidebar
    
    def _create_chat_area(self):
        chat = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Messages
        scroll = QScrollArea()
        scroll.setStyleSheet(f"""
    QScrollArea {{
        background-color: {self.theme['bg_primary']};
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {self.theme['bg_secondary']};
        width: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {self.theme['accent_green']};
        border-radius: 5px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {self.theme['accent_warm']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
""")
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.msg_layout = QVBoxLayout()
        self.msg_layout.setSpacing(12)
        self.msg_layout.addStretch()
        container.setLayout(self.msg_layout)
        scroll.setWidget(container)
        self.scroll_area = scroll
        layout.addWidget(scroll, 1)
        self.file_upload_widget = FileUploadWidget()
        self.file_upload_widget.file_selected.connect(self._on_file_selected)
        self.file_upload_widget.hide()  # Hidden by default
        layout.addWidget(self.file_upload_widget)
        self.file_preview_container = QWidget()
        self.file_preview_layout = QVBoxLayout()
        self.file_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.file_preview_container.setLayout(self.file_preview_layout)
        layout.addWidget(self.file_preview_container)
        
       # Input
        input_frame = QFrame()
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.input = QTextEdit()
        self.input.setPlaceholderText("Message PSA...")
        self.input.setMaximumHeight(100)
        self.input.setStyleSheet(f"""
    QTextEdit {{
        background-color: {self.theme['bg_secondary']};
        color: {self.theme['text_primary']};
        border: 2px solid {self.theme['border']};
        border-radius: 10px;
        padding: 12px;
        font-size: 11pt;
    }}
    QTextEdit:focus {{
        border: 2px solid {self.theme['accent_warm']};
    }}
""")
        self.input.installEventFilter(self)
        input_layout.addWidget(self.input)

# Action buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        action_layout.addStretch()
        
        # File upload (existing, keep as is)
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(40, 40)
        self.attach_btn.setToolTip("Attach file")
        self.attach_btn.setCheckable(True)
        self.attach_btn.clicked.connect(self._toggle_file_upload)
        self.attach_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton:checked {{
                background-color: {self.theme['accent_green']};
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        action_layout.addWidget(self.attach_btn)
        
        # Web search button (NEW!)
        self.web_search_btn = QPushButton("🔍")
        self.web_search_btn.setFixedSize(40, 40)
        self.web_search_btn.setToolTip("Force web search")
        self.web_search_btn.setCheckable(True)
        self.web_search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton:checked {{
                background-color: {self.theme['accent_green']};
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        action_layout.addWidget(self.web_search_btn)
        
        # Voice button (NEW!)
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(40, 40)
        self.voice_btn.setToolTip("Voice input")
        self.voice_btn.clicked.connect(self._handle_voice_input)
        self.voice_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['bg_secondary']};
                color: {self.theme['text_primary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        action_layout.addWidget(self.voice_btn)
        
        # Send button
        self.send_btn = QPushButton("Send 🔤")
        self.send_btn.setFixedHeight(40)
        self.send_btn.setFixedWidth(120)
        self.send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
            QPushButton:disabled {{
                background-color: {self.theme['bg_tertiary']};
            }}
        """)
        self.send_btn.clicked.connect(self._send_message)
        action_layout.addWidget(self.send_btn)
        
        input_layout.addLayout(action_layout)
        input_frame.setLayout(input_layout)
        layout.addWidget(input_frame)

        chat.setLayout(layout)
        chat.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
        return chat
    
    def _create_right_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        self.right_sidebar = sidebar  # ADD THIS LINE
    
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
    
        # Memory panel with collapse button
        mem_header_layout = QHBoxLayout()
    
        # ADD THIS: Collapse button
        self.right_collapse_btn = QPushButton("▶")
        self.right_collapse_btn.setFixedSize(32, 32)
        self.right_collapse_btn.setToolTip("Hide memory")
        self.right_collapse_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {self.theme['bg_secondary']};
            border: 1px solid {self.theme['border']};
            border-radius: 16px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {self.theme['accent_warm']};
        }}
    """)
        self.right_collapse_btn.clicked.connect(self._toggle_right_sidebar)
        mem_header_layout.addWidget(self.right_collapse_btn)
    
        mem_header = QLabel("Your Memory")
        mem_header.setFont(QFont("Segoe UI", 14, weight=700))
        mem_header.setStyleSheet(f"color: {self.theme['accent_warm']};")
        mem_header_layout.addWidget(mem_header)
        mem_header_layout.addStretch()
    
        layout.addLayout(mem_header_layout)
    
        mem_scroll = QScrollArea()
        mem_scroll.setWidgetResizable(True)
        mem_container = QWidget()
        self.mem_header_layout = QVBoxLayout()
        self.mem_header_layout.setSpacing(8)
        mem_container.setLayout(self.mem_header_layout)
        mem_scroll.setWidget(mem_container)
        mem_scroll.setStyleSheet(f"""
    QScrollArea {{
        background-color: {self.theme['bg_primary']};
        border: none;
    }}
""")

        layout.addWidget(mem_scroll, 1)
        sidebar.setLayout(layout)
        sidebar.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
        return sidebar
    
    def _open_settings(self):
        dialog = SettingsDialog(self.bridge, self)
        dialog.theme_changed.connect(self._on_theme_changed)
        dialog.exec()




    def _toggle_right_sidebar(self):
        """Toggle right sidebar visibility"""
        if self.right_sidebar.isVisible():
            self.right_sidebar.hide()
            self.right_collapse_btn.setText("◀")
            self.right_collapse_btn.setToolTip("Show memory")
        
            # Show floating restore button
            if not hasattr(self, 'right_restore_btn'):
                self.right_restore_btn = QPushButton("◀")
                self.right_restore_btn.setFixedSize(40, 40)
                self.right_restore_btn.setToolTip("Show memory")
                self.right_restore_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme['accent_green']};
                    color: {self.theme['text_primary']};
                    border: none;
                    border-radius: 20px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme['accent_warm']};
                }}
            """)
                self.right_restore_btn.clicked.connect(self._toggle_right_sidebar)
                self.right_restore_btn.setParent(self.main_screen)
                # Position at top-right corner
                QTimer.singleShot(100, lambda: self.right_restore_btn.move(
                self.main_screen.width() - 50, 10
                ))
            self.right_restore_btn.show()
        else:
            self.right_sidebar.show()
            self.right_collapse_btn.setText("▶")
            self.right_collapse_btn.setToolTip("Hide memory")
            if hasattr(self, 'right_restore_btn'):
                self.right_restore_btn.hide()


    def _on_theme_changed(self):
        """Handle theme change properly"""
        # Get old theme name for comparison
        old_theme = "dark" if theme_manager.is_dark() else "light"
    
        # Toggle theme
        new_theme_dict = theme_manager.toggle_theme()
        self.theme = new_theme_dict
    
        # Check if actually changed
        new_theme = "dark" if theme_manager.is_dark() else "light"
    
        if old_theme == new_theme:
            QMessageBox.warning(self, "Theme", "Theme didn't change. Try again.")
            return
    
        # Completely recreate main screen
        if self.main_screen:
            # Store current state
            current_conv = self.bridge.current_conv_id
        
            # Remove and delete old screen
            self.stacked.removeWidget(self.main_screen)
            self.main_screen.deleteLater()
            self.main_screen = None
        
        # Small delay for cleanup
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._complete_theme_change(current_conv))

    def _complete_theme_change(self, current_conv):
        """Complete theme change after cleanup"""
        # Recreate fresh
        self.main_screen = self._create_main_screen()
        self.stacked.addWidget(self.main_screen)
        self.stacked.setCurrentWidget(self.main_screen)
    
        # Restore state
        self.conv_metadata = ConversationMetadata(self.bridge.username)
        
    
        # Reload current conversation
        if current_conv:
            messages = self.bridge.load_conversation(current_conv)
            self._display_messages(messages)
    
        self._refresh_conversations_with_pinning()
        self._refresh_memory()
        self._refresh_reminders()
    
        theme_name = "Dark" if theme_manager.is_dark() else "Light"
        QMessageBox.information(self, "Theme Changed", f"✅ Switched to {theme_name} theme!")
    def _conversation_context_menu(self, position):
        item = self.conv_list.itemAt(position)
        if not item:
            return
    
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        if not conv_id:  # Header item
            return
    
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
    
        # Pin/Unpin action
        is_pinned = self.conv_metadata.is_pinned(conv_id) if self.conv_metadata else False
        pin_text = "📍 Unpin" if is_pinned else "📌 Pin to top"
        pin_action = menu.addAction(pin_text)
    
        # Favorite action
        is_fav = self.conv_metadata.is_favorite(conv_id) if self.conv_metadata else False
        fav_text = "☆ Remove from favorites" if is_fav else "⭐ Add to favorites"
        fav_action = menu.addAction(fav_text)
    
        menu.addSeparator()
    
        # Existing actions
        
        export_action = menu.addAction("📤 Export")
        delete_action = menu.addAction("🗑️ Delete")
    
        action = menu.exec(self.conv_list.mapToGlobal(position))
    
        if action == pin_action:
            self._toggle_pin(conv_id)
        elif action == fav_action:
            self._toggle_favorite(conv_id)
        elif action == export_action:
            # Save current conv_id and export
            old_conv = self.bridge.current_conv_id
            self.bridge.current_conv_id = conv_id
            self._export_conversation()
            self.bridge.current_conv_id = old_conv
        elif action == delete_action:
            self._delete_conversation(conv_id)
    
    def _rename_conversation(self, conv_id: str, current_title: str):
        new_title, ok = QInputDialog.getText(self, "Rename Conversation", "New title:", text=current_title)
        if ok and new_title.strip():
            if self.bridge.rename_conversation(conv_id, new_title.strip()):
                self._refresh_conversations_with_pinning()
    
    def _delete_conversation(self, conv_id: str):
        reply = QMessageBox.question(self, "Delete Conversation",
                                      "Are you sure you want to delete this conversation?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.bridge.delete_conversation(conv_id):
                self._refresh_conversations_with_pinning()
                if self.bridge.current_conv_id == conv_id:
                    self._new_conversation()
    
    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._send_message()
                return True
        return super().eventFilter(obj, event)
    
    def _new_conversation(self):
        self.bridge.create_new_conversation()
        self._refresh_conversations_with_pinning()
        self._clear_messages()
    
    def _on_conversation_selected(self, item):
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        messages = self.bridge.load_conversation(conv_id)
        self._display_messages(messages)
    
    def _refresh_conversations_with_pinning(self):
        """Refresh conversations list with pinning support"""
        self.conv_list.clear()
    
        if not self.conv_metadata:
            # Fallback to simple list if metadata not initialized
            self._refresh_conversations_simple()
            return
    
        # Get all conversations
        all_convs = self.bridge.get_all_conversations()
    
        # Separate pinned and unpinned
        pinned_ids = set(self.conv_metadata.get_pinned())
        favorite_ids = set(self.conv_metadata.get_favorites())
    
        pinned_convs = []
        unpinned_convs = []
    
        for conv_id, title in all_convs:
            if conv_id in pinned_ids:
                pinned_convs.append((conv_id, title))
            else:
                unpinned_convs.append((conv_id, title))
    
        # Add pinned conversations first
        if pinned_convs:
            # Pinned section header
            header_item = QListWidgetItem("📌 PINNED")
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setFont(QFont("Segoe UI", 9, weight=700))
            self.conv_list.addItem(header_item)
        
        for conv_id, title in pinned_convs:
            self._add_conversation_item(
                conv_id, title, 
                is_pinned=True,
                is_favorite=(conv_id in favorite_ids)
            )
    
        # Add unpinned conversations
        if unpinned_convs:
            if pinned_convs:
                separator_item = QListWidgetItem("💬 ALL CONVERSATIONS")
                separator_item.setFlags(Qt.ItemFlag.NoItemFlags)
                separator_item.setFont(QFont("Segoe UI", 9, weight=700))
                self.conv_list.addItem(separator_item)
        
        for conv_id, title in unpinned_convs:
            self._add_conversation_item(
                conv_id, title,
                is_pinned=False,
                is_favorite=(conv_id in favorite_ids)
            )

    def _refresh_conversations_simple(self):
        """Refresh conversations with EXPLICIT text styling"""
        self.conv_list.clear()
        convs = self.bridge.get_all_conversations()
    
        for conv_id, title in convs:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, conv_id)
        
            # CRITICAL: Set explicit text color
            item.setForeground(QBrush(QColor(self.theme['text_primary'])))
        
            # CRITICAL: Set explicit font with large size
            font = QFont("Segoe UI", 12, weight=600)  # Size 12, Bold
            item.setFont(font)
        
            # CRITICAL: Set minimum height
            item.setSizeHint(QSize(0, 40))
        
            self.conv_list.addItem(item)
    def _add_conversation_item(self, conv_id: str, title: str, 
                       is_pinned: bool, is_favorite: bool):
        """Add a conversation item (simplified version)"""
    
        # Build display text with indicators
        display_text = ""
        if is_pinned:
            display_text += "📌 "
        if is_favorite:
            display_text += "⭐ "
        display_text += title
    
        # Create simple list item
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, conv_id)
    
    # Set styling
        from PyQt6.QtGui import QBrush, QColor
        item.setForeground(QBrush(QColor(self.theme['text_primary'])))
    
        font = QFont("Segoe UI", 11, weight=600)
        item.setFont(font)
    
        from PyQt6.QtCore import QSize
        item.setSizeHint(QSize(0, 40))
    
        self.conv_list.addItem(item)
   

# ============================================================================
#   SEARCH & EXPORT
# ============================================================================

    def _search_conversations(self):
        """Open search dialog (Ctrl+F)"""
        from search_export import ConversationSearchDialog
    
        dialog = ConversationSearchDialog(self.bridge, self)
        dialog.conversation_selected.connect(self._load_searched_conversation)
        dialog.exec()

    def _load_searched_conversation(self, conv_id: str):
        """Load conversation from search results"""
        messages = self.bridge.load_conversation(conv_id)
        self._display_messages(messages)

    def _export_conversation(self):
        """Export current conversation (Ctrl+E)"""
        from search_export import ExportDialog
    
        if not self.bridge.current_conv_id:
            QMessageBox.warning(self, "No Conversation", "No conversation to export!")
            return
    
        dialog = ExportDialog(self.bridge, self.bridge.current_conv_id, self)
        dialog.exec()

# ============================================================================
#   PINNING & FAVORITES
# ============================================================================

    def _toggle_pin(self, conv_id: str):
        """Toggle pin status for a conversation"""
        if not self.conv_metadata:
            return
    
        self.conv_metadata.toggle_pin(conv_id)
        self._refresh_conversations_with_pinning()
    
        is_pinned = self.conv_metadata.is_pinned(conv_id)
        

    def _toggle_favorite(self, conv_id: str):
        """Toggle favorite status for a conversation"""
        if not self.conv_metadata:
         return
    
        self.conv_metadata.toggle_favorite(conv_id)
        self._refresh_conversations_with_pinning()
    
        is_fav = self.conv_metadata.is_favorite(conv_id)
        

    def _load_conversation_by_id(self, conv_id: str):
        """Load a conversation by its ID"""
        messages = self.bridge.load_conversation(conv_id)
        self._display_messages(messages)

    def _pin_current_conversation(self):
        """Pin/unpin current conversation (Ctrl+P)"""
        if not self.bridge.current_conv_id or not self.conv_metadata:
         return
    
        self._toggle_pin(self.bridge.current_conv_id)

    def _filter_favorites(self):
        """Show only favorite conversations (Ctrl+Shift+F)"""
        if not self.conv_metadata:
            return
    
        self.showing_favorites_only = not self.showing_favorites_only
    
        if self.showing_favorites_only:
            self._show_favorites_only()
            
        else:
            self._refresh_conversations_with_pinning()
            

    def _show_favorites_only(self):
        """Filter to show only favorites"""
        self.conv_list.clear()
    
        favorite_ids = set(self.conv_metadata.get_favorites())
        all_convs = self.bridge.get_all_conversations()
    
        # Header
        header_item = QListWidgetItem("⭐ FAVORITES")
        header_item.setFlags(Qt.ItemFlag.NoItemFlags)
        header_item.setFont(QFont("Segoe UI", 9, weight=700))
        self.conv_list.addItem(header_item)
    
        # Add favorites
        for conv_id, title in all_convs:
           if conv_id in favorite_ids:
                self._add_conversation_item(
                conv_id, title,
                is_pinned=self.conv_metadata.is_pinned(conv_id),
                is_favorite=True
                )

# ============================================================================
#   ADVANCED SETTINGS & ABOUT
# ============================================================================

    
    def analyze_file_with_psa_personality(username: str,user_memory:dict,file_path: str,user_message: str,conv_id: str,recent_context: str = "") -> str:
        """
        Simple function to analyze file with PSA personality.
    
        Args:
        username: Current user
        user_memory: User's memory dict
        file_path: Path to uploaded file
        user_message: User's message about the file
        conv_id: Current conversation ID
        recent_context: Recent conversation context
    
        Returns:
            Personalized response from PSA
        """
        try:
            psa_vision = FileUploadWidget(username, user_memory, vision_provider='gemini')
            return psa_vision.analyze_file_with_personality(
            file_path,
            user_message,
            conv_id,
            recent_context
            )
        except Exception as e:
            return f"Oops! I had trouble analyzing that file. Error: {e}"
    def _refresh_memory(self):
        while self.mem_header_layout.count():
            child = self.mem_header_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        memory = self.bridge.get_memory()
        icons = {"name": "👤", "likes": "❤️", "dislikes": "👎", "hobbies": "🎮", "goals": "🎯", "facts": "ℹ️"}
        
        for cat in ["name", "likes", "dislikes", "hobbies", "goals", "facts"]:
            values = memory.get(cat, [])
            if values:
                cat_label = QLabel(f"{icons[cat]} {cat.upper()}")
                cat_label.setFont(QFont("Segoe UI", 10, weight=700))
                cat_label.setStyleSheet(f"color: {self.theme['accent_warm']};")
                self.mem_header_layout.addWidget(cat_label)
                
                for val in values:
                    card = MemoryCard(cat, val)
                    card.delete_requested.connect(self._delete_memory)
                    card.edit_requested.connect(self._edit_memory)
                    self.mem_header_layout.addWidget(card)
                
                spacer = QLabel("")
                spacer.setFixedHeight(8)
                self.mem_header_layout.addWidget(spacer)
        
        self.mem_header_layout.addStretch()
    
    def _refresh_reminders(self):
        self.rem_list.clear()
        reminders = self.bridge.get_reminders()
        for r in reminders:
            self.rem_list.addItem(f"🔔 {r['text']} @ {r['datetime']}")
    
    def _clear_messages(self):
        while self.msg_layout.count() > 1:
            child = self.msg_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _display_messages(self, messages):
        self._clear_messages()
        for msg in messages:
            self._add_message_bubble(msg['role'], msg['content'], save=False)
    
    def _add_message_bubble(self, role: str, content: str, save=True) -> MessageBubble:
        timestamp = datetime.now().isoformat()
        bubble = MessageBubble(role, content, timestamp)
        bubble.regenerate_requested.connect(self._regenerate_response)
        bubble.read_requested.connect(self._read_aloud)
        
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, bubble)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
        
        return bubble
    
    def _regenerate_response(self, previous_content: str):
        for i in range(self.msg_layout.count() - 2, -1, -1):
            widget = self.msg_layout.itemAt(i).widget()
            if isinstance(widget, MessageBubble) and widget.role == "user":
                user_text = widget.content
                next_widget = self.msg_layout.itemAt(i + 1).widget()
                if isinstance(next_widget, MessageBubble) and next_widget.role == "assistant":
                    next_widget.deleteLater()
                self._stream_response(user_text)
                break
    
    # Old version (doesn't work):
    def _read_aloud(self, text: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

# New version (works perfectly):
    def _read_aloud(self, text: str):
        from advanced_tts import speak
        # Auto-detects language and speaks in appropriate voice
        speak(text, blocking=False)
    
    def _send_message(self):
        text = self.input.toPlainText().strip()
    
        # ========== HANDLE FILE UPLOAD ==========
        if self.current_file:
        # Import here to avoid circular import
            from vision_file_system import analyze_file_with_psa_personality
        
        # Get user memory for context
            user_memory = self.bridge.get_memory()
        
            # Get recent conversation context
            try:
             recent_msgs = self.bridge.get_conversation()[-5:]  # Last 5 messages
             recent_context = "\n".join([
                f"{msg['role']}: {msg['content'][:100]}" 
                for msg in recent_msgs
                ])
            except:
                recent_context = ""
        
            # Analyze file with PSA personality
            try:
                file_analysis = analyze_file_with_psa_personality(
                username=self.bridge.username,
                user_memory=user_memory,
                file_path=self.current_file,
                user_message=text,
                conv_id=self.bridge.current_conv_id,
                recent_context=recent_context
            )
            except Exception as e:
                file_analysis = f"Sorry, I had trouble analyzing that file."
        
            # Add user message with file indicator
            file_name = Path(self.current_file).name
            user_message = f"{text}\n\n📎 Attached: {file_name}" if text else f"📎 Attached: {file_name}"
        
            self._add_message_bubble("user", user_message)
            self._add_message_bubble("assistant", file_analysis)
        
            # Save to conversation
            try:
                self.bridge.add_user_message(user_message)
                add_message(self.bridge.username, self.bridge.current_conv_id, "assistant", file_analysis)
            except Exception as e:
                print(f"Error saving to conversation: {e}")
        
            # Clear file and input
            self._remove_file()
            self.input.clear()
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            return
        # Handle web search button
        if self.web_search_btn.isChecked():
            text = f"search for {text}"
            self.web_search_btn.setChecked(False)  
        # ========== NORMAL MESSAGE FLOW ==========
        if not text or not self.bridge.current_conv_id:
            return
    
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        
        self._add_message_bubble("user", text)
        track_message_sent()
        self.input.clear()
    
        # Check for reminder
        reminder_response = self.bridge.add_user_message(text)
        if reminder_response:
            self._add_message_bubble("assistant", reminder_response)
            self._refresh_reminders()
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            return
    
        # Stream response
        self._stream_response(text)
    def _toggle_file_upload(self):
        """Toggle file upload widget visibility"""
        if self.attach_btn.isChecked():
            self.file_upload_widget.show()
        else:
                self.file_upload_widget.hide()

    def _on_file_selected(self, file_path: str):
        """Handle file selection"""
        self.current_file = file_path
    
        # Hide upload widget
        self.file_upload_widget.hide()
        self.attach_btn.setChecked(False)
    
        # Show preview
        self._show_file_preview(file_path)
    
        # Auto-focus input
        self.input.setFocus()
    def _handle_voice_input(self):
        """Handle voice input button"""
        self.voice_btn.setEnabled(False)
        self.voice_btn.setText("⏺️")
        self.voice_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: #ff6b6b;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
        }}
    """)
    
        old_title = self.windowTitle()
        self.setWindowTitle("🎤 Recording...")
    
        from PyQt6.QtCore import QThread, pyqtSignal
    
        class VoiceThread(QThread):
            finished = pyqtSignal(str)
        
            def run(self):
                try:
                    text = quick_voice_input(duration=10)
                    self.finished.emit(text or "")
                except Exception as e:
                    print(f"Voice error: {e}")
                    self.finished.emit("")
    
        self.voice_thread = VoiceThread()
        self.voice_thread.finished.connect(self._on_voice_completed)
        self.voice_thread.start()

    def _on_voice_completed(self, text: str):
        """Handle voice result"""
        self.voice_btn.setEnabled(True)
        self.voice_btn.setText("🎤")
        self.voice_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {self.theme['bg_secondary']};
            color: {self.theme['text_primary']};
            border: 1px solid {self.theme['border']};
            border-radius: 8px;
            font-size: 16px;
        }}
        QPushButton:hover {{
            background-color: {self.theme['accent_warm']};
        }}
    """)
        self.setWindowTitle("PSA - Personal Smart Assistant")
    
        if text:
            self.input.setPlainText(text)
            self.input.setFocus()
    def _show_file_preview(self, file_path: str):
        """Show file preview"""
        # Clear existing preview
        self._clear_file_preview()
    
        # Create new preview
        self.file_preview = FilePreviewWidget(file_path)
        self.file_preview.remove_requested.connect(self._remove_file)
        self.file_preview_layout.addWidget(self.file_preview)

    def _remove_file(self):
        """Remove attached file"""
        self.current_file = None
        self._clear_file_preview()

    def _clear_file_preview(self):
        """Clear file preview"""
        if self.file_preview:
            self.file_preview.deleteLater()
            self.file_preview = None

    def _stream_response(self, user_input: str):
        # Show typing indicator
        
    
        self.current_assistant_bubble = self._add_message_bubble("assistant", "")
        conversation = self.bridge.get_conversation()
        recent_history = []
        for msg in conversation[-20:]:
           recent_history.append({"role":msg["role"],"content":msg["content"]})
    
        self.streaming_thread = StreamingThread(self.bridge, user_input, recent_history)
        self.streaming_thread.chunk_received.connect(self._on_chunk_received)
        self.streaming_thread.finished_signal.connect(self._on_streaming_finished)
        self.streaming_thread.error_occurred.connect(self._on_streaming_error)
        self.streaming_thread.start()

    def _on_streaming_finished(self):
        self._hide_typing_indicator()
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.current_assistant_bubble = None
        self._refresh_memory()

    def _on_streaming_error(self, error_msg: str):
        self._hide_typing_indicator()
    
        if self.current_assistant_bubble:
            current_text = self.current_assistant_bubble.content + "\n\n⚠️ " + error_msg
            self.current_assistant_bubble.update_content(current_text)
    
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
    

    
    
    def _on_chunk_received(self, chunk: str):
        if self.current_assistant_bubble:
            current_text = self.current_assistant_bubble.content + chunk
            self.current_assistant_bubble.update_content(current_text)
            self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
    
    def _on_streaming_finished(self):
        
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.current_assistant_bubble = None
        self._refresh_memory()
        
    def _on_streaming_error(self, error_msg: str):
        if self.current_assistant_bubble:
            current_text = self.current_assistant_bubble.content + error_msg
            self.current_assistant_bubble.update_content(current_text)
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
    
    def _delete_memory(self, category: str, value: str):
        reply = QMessageBox.question(self, "Delete Memory", f"Delete '{value}' from {category}?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.bridge.delete_memory(category, value):
                self._refresh_memory()
    
    def _edit_memory(self, category: str, old_value: str):
        new_value, ok = QInputDialog.getText(self, "Edit Memory", f"Edit {category}:", text=old_value)
        if ok and new_value.strip():
            if self.bridge.edit_memory(category, old_value, new_value.strip()):
                self._refresh_memory()
    
    def _logout(self):
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.bridge.logout()
            self.stacked.setCurrentWidget(self.login_screen)
            self.login_screen.username_input.clear()
            self.login_screen.password_input.clear()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setOrganizationName("PSA")
    app.setApplicationName("PersonalSmartAssistant")
    
    # Suppress comtypes warnings
    import logging
    logging.getLogger('comtypes').setLevel(logging.ERROR)
    
    window = PSAMainApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()