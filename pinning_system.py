"""
PSA Conversation Pinning & Favorites System
Pin important conversations to the top + star favorites
"""

import json
from pathlib import Path
from typing import List, Set
from PyQt6.QtWidgets import (
    QListWidgetItem, QWidget, QHBoxLayout, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
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
#   PINNED CONVERSATIONS STORAGE
# ===========================================================================

class ConversationMetadata:
    """Manage conversation metadata (pinned, favorited)"""
    
    def __init__(self, username: str):
        self.username = username
        self.metadata_file = Path(f"conversation_metadata_{username}.json")
        self.metadata = self._load()
    
    def _load(self) -> dict:
        """Load metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {'pinned': [], 'favorites': [], 'tags': {}}
        return {'pinned': [], 'favorites': [], 'tags': {}}
    
    def _save(self):
        """Save metadata to file"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
    
    def is_pinned(self, conv_id: str) -> bool:
        """Check if conversation is pinned"""
        return conv_id in self.metadata.get('pinned', [])
    
    def is_favorite(self, conv_id: str) -> bool:
        """Check if conversation is favorited"""
        return conv_id in self.metadata.get('favorites', [])
    
    def pin(self, conv_id: str):
        """Pin a conversation"""
        if conv_id not in self.metadata['pinned']:
            self.metadata['pinned'].append(conv_id)
            self._save()
    
    def unpin(self, conv_id: str):
        """Unpin a conversation"""
        if conv_id in self.metadata['pinned']:
            self.metadata['pinned'].remove(conv_id)
            self._save()
    
    def toggle_pin(self, conv_id: str):
        """Toggle pin status"""
        if self.is_pinned(conv_id):
            self.unpin(conv_id)
        else:
            self.pin(conv_id)
    
    def favorite(self, conv_id: str):
        """Add to favorites"""
        if conv_id not in self.metadata['favorites']:
            self.metadata['favorites'].append(conv_id)
            self._save()
    
    def unfavorite(self, conv_id: str):
        """Remove from favorites"""
        if conv_id in self.metadata['favorites']:
            self.metadata['favorites'].remove(conv_id)
            self._save()
    
    def toggle_favorite(self, conv_id: str):
        """Toggle favorite status"""
        if self.is_favorite(conv_id):
            self.unfavorite(conv_id)
        else:
            self.favorite(conv_id)
    
    def get_pinned(self) -> List[str]:
        """Get list of pinned conversation IDs"""
        return self.metadata.get('pinned', [])
    
    def get_favorites(self) -> List[str]:
        """Get list of favorite conversation IDs"""
        return self.metadata.get('favorites', [])
    
    def add_tag(self, conv_id: str, tag: str):
        """Add a tag to conversation"""
        if conv_id not in self.metadata['tags']:
            self.metadata['tags'][conv_id] = []
        
        if tag not in self.metadata['tags'][conv_id]:
            self.metadata['tags'][conv_id].append(tag)
            self._save()
    
    def remove_tag(self, conv_id: str, tag: str):
        """Remove a tag from conversation"""
        if conv_id in self.metadata['tags']:
            if tag in self.metadata['tags'][conv_id]:
                self.metadata['tags'][conv_id].remove(tag)
                self._save()
    
    def get_tags(self, conv_id: str) -> List[str]:
        """Get tags for a conversation"""
        return self.metadata['tags'].get(conv_id, [])


# ===========================================================================
#   ENHANCED CONVERSATION LIST ITEM
# ===========================================================================

class ConversationListItem(QWidget):
    """Custom list item with pin/favorite buttons"""
    
    pin_clicked = pyqtSignal(str)  # conv_id
    favorite_clicked = pyqtSignal(str)  # conv_id
    item_clicked = pyqtSignal(str)  # conv_id
    
    def __init__(self, conv_id: str, title: str, is_pinned: bool, 
                 is_favorite: bool, parent=None):
        super().__init__(parent)
        self.conv_id = conv_id
        self.title = title
        self.is_pinned = is_pinned
        self.is_favorite = is_favorite
        self.theme = get_theme(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Pin indicator
        if self.is_pinned:
            pin_label = QLabel("📌")
            pin_label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(pin_label)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 10))
        title_label.setStyleSheet(f"color: {self.theme['text_primary']};")
        title_label.mousePressEvent = lambda e: self.item_clicked.emit(self.conv_id)
        layout.addWidget(title_label, 1)
        
        # Favorite button (star)
        self.fav_btn = QPushButton("⭐" if self.is_favorite else "☆")
        self.fav_btn.setFixedSize(24, 24)
        self.fav_btn.setToolTip("Add to favorites" if not self.is_favorite else "Remove from favorites")
        self.fav_btn.clicked.connect(lambda: self.favorite_clicked.emit(self.conv_id))
        self.fav_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_tertiary']};
                border-radius: 4px;
            }}
        """)
        self.fav_btn.hide()  # Show on hover
        layout.addWidget(self.fav_btn)
        
        # Pin button
        self.pin_btn = QPushButton("📌" if not self.is_pinned else "📍")
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip("Pin to top" if not self.is_pinned else "Unpin")
        self.pin_btn.clicked.connect(lambda: self.pin_clicked.emit(self.conv_id))
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['bg_tertiary']};
                border-radius: 4px;
            }}
        """)
        self.pin_btn.hide()  # Show on hover
        layout.addWidget(self.pin_btn)
        
        self.setLayout(layout)
    
    def enterEvent(self, event):
        """Show buttons on hover"""
        self.fav_btn.show()
        self.pin_btn.show()
    
    def leaveEvent(self, event):
        """Hide buttons when not hovering"""
        self.fav_btn.hide()
        self.pin_btn.hide()
    
    def update_pin_status(self, is_pinned: bool):
        """Update pin status"""
        self.is_pinned = is_pinned
        self.pin_btn.setText("📌" if not is_pinned else "📍")
        self.pin_btn.setToolTip("Pin to top" if not is_pinned else "Unpin")
    
    def update_favorite_status(self, is_favorite: bool):
        """Update favorite status"""
        self.is_favorite = is_favorite
        self.fav_btn.setText("⭐" if is_favorite else "☆")
        self.fav_btn.setToolTip("Add to favorites" if not is_favorite else "Remove from favorites")
