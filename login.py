#!/usr/bin/env python3
"""
PSA Login Screen - Entry point with authentication
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor

from bridge import PSABackendBridge

DARK_THEME = {
    "bg_primary": "#1a2b2a",
    "bg_secondary": "#243535",
    "bg_tertiary": "#2d4444",
    "text_primary": "#f5f5f0",
    "text_secondary": "#b8b5ad",
    "accent_warm": "#d4a574",
    "accent_green": "#6b9e8a",
    "border": "#3a5555",
}


class LoginScreen(QWidget):
    """Login/Signup screen"""
    
    def __init__(self, bridge: PSABackendBridge, on_login_success):
        super().__init__()
        self.bridge = bridge
        self.on_login_success = on_login_success
        self.theme = DARK_THEME
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 100, 60, 100)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("PSA")
        title.setFont(QFont("Segoe UI", 48, weight=700))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {self.theme['accent_warm']};")
        layout.addWidget(title)
        
        subtitle = QLabel("Personal Smart Assistant")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {self.theme['text_secondary']};")
        layout.addWidget(subtitle)
        
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
        self.username_input.setStyleSheet(f"""
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
        """)
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        password_label.setFont(QFont("Segoe UI", 11, weight=600))
        password_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFont(QFont("Segoe UI", 11))
        self.password_input.setMinimumHeight(40)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(f"""
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
        """)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        login_btn = QPushButton("Login")
        login_btn.setFont(QFont("Segoe UI", 11, weight=600))
        login_btn.setMinimumHeight(44)
        login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_green']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_warm']};
            }}
        """)
        login_btn.clicked.connect(self._on_login)
        button_layout.addWidget(login_btn, 1)
        
        signup_btn = QPushButton("Create Account")
        signup_btn.setFont(QFont("Segoe UI", 11, weight=600))
        signup_btn.setMinimumHeight(44)
        signup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        signup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_warm']};
                color: {self.theme['text_primary']};
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_green']};
            }}
        """)
        signup_btn.clicked.connect(self._on_signup)
        button_layout.addWidget(signup_btn, 1)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {self.theme['bg_primary']};")
    
    def _on_login(self):
        """Handle login"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        ok, msg = self.bridge.authenticate(username, password)
        if ok:
            print(f"âœ“ {msg}")
            self.on_login_success()
        else:
            QMessageBox.warning(self, "Login Failed", msg)
    
    def _on_signup(self):
        """Handle signup"""
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
            print(f"âœ“ {msg}")
            self.on_login_success()
        else:
            QMessageBox.warning(self, "Signup Failed", msg)