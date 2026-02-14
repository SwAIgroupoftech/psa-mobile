"""
PSA Backend Integration Layer
Bridges the PyQt6 UI with the core.py backend
Handles all data flow, conversions, and error management
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal

# Add core modules to path
CORE_PATH = Path(__file__).parent / "core"
if CORE_PATH not in sys.path:
    sys.path.insert(0, str(CORE_PATH.parent))

from core import AppCore
from conversations import (
    create_conversation,
    add_message,
    get_conversation,
    get_conversation_titles,
    delete_conversation,
    rename_conversation,
    load_conversation_summary,
    create_conversation_summary,
   
)
from users import (
    signup,
    login,
    load_memory,
    save_memory,
    detect_and_update_intelligent_memory,
)
from reminder import (
    load_reminders,
    save_reminders,
    handle_reminder_input,
)


class PSABackendBridge:
    """
    Central bridge between PyQt6 UI and PSA backend.
    Handles authentication, data persistence, and streaming.
    """
    
    def __init__(self):
        self.core = AppCore()
        self.username = None
        self.current_conv_id = None
    
    # ========================================================================
    #   AUTHENTICATION
    # ========================================================================
    
    def authenticate(self, username: str, password: str, create_if_missing: bool = False) -> tuple[bool, str]:
        """Login or signup user."""
        ok, msg = self.core.login(username, password, create_if_missing)
        if ok:
            self.username = username
            self.core.set_current_conversation(None)
        return ok, msg
    
    def logout(self):
        """Logout current user."""
        self.core.logout()
        self.username = None
        self.current_conv_id = None
    
    # ========================================================================
    #   CONVERSATION MANAGEMENT
    # ========================================================================
    
    def create_new_conversation(self) -> str:
        """Create a new conversation and return its ID."""
        if not self.username:
            raise RuntimeError("Not authenticated")
        conv_id = create_conversation(self.username)
        self.current_conv_id = conv_id
        self.core.set_current_conversation(conv_id)
        return conv_id
    
    def get_all_conversations(self) -> List[tuple[str, str]]:
        """Get list of (conv_id, title) for sidebar."""
        if not self.username:
            return []
        return get_conversation_titles(self.username)
    def get_conversation(self):
        return get_conversation(self.username,self.current_conv_id)
    
    def load_conversation(self, conv_id: str) -> List[Dict[str, str]]:
        """Load all messages from a conversation."""
        if not self.username:
            return []
        self.current_conv_id = conv_id
        self.core.set_current_conversation(conv_id)
        
        messages = get_conversation(self.username, conv_id)
        # Ensure summary is created for context
        create_conversation_summary(self.username, conv_id)
        return messages
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation."""
        if not self.username:
            return False
        try:
            delete_conversation(self.username, conv_id)
            if self.current_conv_id == conv_id:
                self.current_conv_id = None
            return True
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def rename_conversation(self, conv_id: str, new_title: str) -> bool:
        """Rename a conversation."""
        if not self.username:
            return False
        try:
            rename_conversation(self.username, conv_id, new_title)
            return True
        except Exception as e:
            print(f"Error renaming conversation: {e}")
            return False
    
    
    
    # ========================================================================
    #   MESSAGE OPERATIONS
    # ========================================================================
    

    
    def add_user_message(self, content: str) -> str:
        """Add a user message to current conversation."""
        if not self.username or not self.current_conv_id:
            raise RuntimeError("No active conversation")
        
        add_message(self.username, self.current_conv_id, "user", content)
        
        # Trigger intelligent memory update (if enabled)
        if self.core.enable_memory_update:
            self.core.memories = detect_and_update_intelligent_memory(
                content,
                self.core.memories,
                self.username,
                self.core.password,
            )
        
        # Check for reminder pattern
        if content.lower().startswith("remind"):
            try:
                reminder_msg = handle_reminder_input(content, self.username)
                # Load updated reminders
                self.core.reminders = load_reminders(self.username)
                return reminder_msg
            except Exception as e:
                print(f"Reminder error: {e}")
        
        return None
    
    def stream_assistant_response(self, user_input,recent_history):
        """
        Get streaming assistant response and persist full message.
        Yields chunks as they arrive.
        """
        if not self.username or not self.current_conv_id:
            raise RuntimeError("No active conversation")
        
        # Stream from core
        full_response = ""
        conversation = self.get_conversation()
        recent_history = []
        for msg in conversation[-20:]:
            recent_history.append({"role":msg["role"],"content":msg["content"]})


        for chunk in self.core.get_psa_stream(user_input,recent_history):
            full_response += chunk
            yield chunk
        
        # Persist complete message
        add_message(self.username, self.current_conv_id, "assistant", full_response)
        
        # Update conversation summary periodically
        create_conversation_summary(self.username, self.current_conv_id)
    
    # ========================================================================
    #   MEMORY OPERATIONS
    # ========================================================================
    
    def get_memory(self) -> Dict[str, List[str]]:
        """Get current user's memory."""
        if not self.username:
            return {}
        return load_memory(self.username, self.core.password)
    
    def add_memory(self, category: str, value: str) -> bool:
        """Manually add a memory item."""
        if not self.username:
            return False
        try:
            self.core.memories = load_memory(self.username, self.core.password)
            if value not in self.core.memories.get(category, []):
                self.core.memories.setdefault(category, []).append(value)
                save_memory(self.core.memories, self.username, self.core.password)
            return True
        except Exception as e:
            print(f"Error adding memory: {e}")
            return False
    
    def delete_memory(self, category: str, value: str) -> bool:
        """Delete a memory item."""
        if not self.username:
            return False
        try:
            self.core.memories = load_memory(self.username, self.core.password)
            if value in self.core.memories.get(category, []):
                self.core.memories[category].remove(value)
                save_memory(self.core.memories, self.username, self.core.password)
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def edit_memory(self, category: str, old_value: str, new_value: str) -> bool:
        """Edit a memory item."""
        if not self.username:
            return False
        return self.delete_memory(category, old_value) and self.add_memory(category, new_value)
    
    # ========================================================================
    #   REMINDER OPERATIONS
    # ========================================================================
    
    def get_reminders(self) -> List[Dict[str, str]]:
        """Get all upcoming reminders."""
        if not self.username:
            return []
        return load_reminders(self.username)
    
    def add_reminder_manual(self, text: str, datetime_str: str) -> bool:
        """Manually add a reminder (datetime format: YYYY-MM-DD HH:MM)."""
        if not self.username:
            return False
        try:
            self.core.reminders = load_reminders(self.username)
            self.core.reminders.append({"text": text, "datetime": datetime_str})
            save_reminders(self.username, self.core.reminders)
            return True
        except Exception as e:
            print(f"Error adding reminder: {e}")
            return False
    
    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder by index."""
        if not self.username:
            return False
        try:
            self.core.reminders = load_reminders(self.username)
            if 0 <= reminder_id < len(self.core.reminders):
                self.core.reminders.pop(reminder_id)
                save_reminders(self.username, self.core.reminders)
                return True
        except Exception as e:
            print(f"Error deleting reminder: {e}")
        return False
    
    # ========================================================================
    #   SETTINGS
    # ========================================================================
    
    def set_memory_enabled(self, enabled: bool):
        """Enable/disable automatic memory updates."""
        self.core.set_memory_update(enabled)
    
    def set_private_mode(self, enabled: bool):
        """Enable/disable private mode (disables memory tracking)."""
        self.core.set_private_mode(enabled)
    
    # ========================================================================
    #   UTILITY
    # ========================================================================
    
    def is_authenticated(self) -> bool:
        """Check if user is logged in."""
        return self.username is not None
    
    def get_current_username(self) -> Optional[str]:
        """Get logged-in username."""
        return self.username


# ========================================================================
#   STREAMING HELPER FOR UI
# ========================================================================

from PyQt6.QtCore import QThread, pyqtSignal


class StreamingThread(QThread):
    """
    Run streaming response in background thread to prevent UI freezing.
    """
    chunk_received = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, bridge: PSABackendBridge, user_input: str,recent_history):
        super().__init__()
        self.bridge = bridge
        self.user_input = user_input
        conversation = self.bridge.get_conversation()
        recent_history = []
        for msg in conversation[-20:]:
            recent_history.append({"role":msg["role"],"content":msg["content"]})
        else:
            recent_history = None

        self.recent_history = recent_history
        self.full_response = ""
    
    def run(self):
        try:
            for chunk in self.bridge.stream_assistant_response(self.user_input,self.recent_history):
                self.full_response += chunk
                self.chunk_received.emit(chunk)
            self.finished_signal.emit()
        except Exception as e:
            self.error_occurred.emit(f"\nâš ï¸ Error: {str(e)}")
            self.finished_signal.emit()


if __name__ == "__main__":
    # Quick test
    bridge = PSABackendBridge()
    print("PSA Backend Bridge initialized successfully!")
    print(f"Methods: {[m for m in dir(bridge) if not m.startswith('_')]}")