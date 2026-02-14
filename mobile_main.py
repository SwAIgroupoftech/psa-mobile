"""
PSA Mobile - Kivy Version
Personal Smart Assistant for Android/iOS
"""

import os
os.environ['KIVY_NO_CONSOLELOG'] = '1'  # Reduce console spam

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp

import threading
from datetime import datetime
from pathlib import Path

# Import your existing PSA backend
from core import start_reminder_service
from bridge import PSABackendBridge
from conversations import get_conversation, add_message
from users import UserManager, get_current_user
from file_memory_db import FileMemoryDB

# ===========================================================================
# CONFIGURATION
# ===========================================================================

COLORS = {
    'primary': get_color_from_hex('#2196F3'),
    'primary_dark': get_color_from_hex('#1976D2'),
    'accent': get_color_from_hex('#FF4081'),
    'background': get_color_from_hex('#FAFAFA'),
    'surface': get_color_from_hex('#FFFFFF'),
    'text_primary': get_color_from_hex('#212121'),
    'text_secondary': get_color_from_hex('#757575'),
    'divider': get_color_from_hex('#BDBDBD'),
    'user_bubble': get_color_from_hex('#E3F2FD'),
    'ai_bubble': get_color_from_hex('#F5F5F5'),
    'success': get_color_from_hex('#4CAF50'),
    'error': get_color_from_hex('#F44336'),
}

# ===========================================================================
# CUSTOM WIDGETS
# ===========================================================================

class RoundedButton(Button):
    """Custom rounded button with elevation"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = COLORS['primary']
        self.color = COLORS['surface']
        self.size_hint_y = None
        self.height = dp(48)
        self.font_size = sp(16)
        
        with self.canvas.before:
            Color(*COLORS['primary'])
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(24)])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class MessageBubble(BoxLayout):
    """Chat message bubble"""
    text = StringProperty('')
    is_user = BooleanProperty(False)
    timestamp = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = dp(12)
        self.spacing = dp(4)
        
        # Determine alignment and color
        if self.is_user:
            self.size_hint_x = 0.75
            self.pos_hint = {'right': 1}
            bg_color = COLORS['user_bubble']
        else:
            self.size_hint_x = 0.85
            self.pos_hint = {'x': 0}
            bg_color = COLORS['ai_bubble']
        
        # Background
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Message text
        msg_label = Label(
            text=self.text,
            color=COLORS['text_primary'],
            size_hint_y=None,
            markup=True,
            text_size=(self.width - dp(24), None),
            halign='left',
            valign='top',
            font_size=sp(15)
        )
        msg_label.bind(
            width=lambda *x: msg_label.setter('text_size')(msg_label, (msg_label.width, None)),
            texture_size=lambda *x: msg_label.setter('height')(msg_label, msg_label.texture_size[1])
        )
        self.add_widget(msg_label)
        
        # Timestamp
        time_label = Label(
            text=self.timestamp,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(16),
            font_size=sp(11),
            halign='right' if self.is_user else 'left'
        )
        self.add_widget(time_label)
        
        # Calculate bubble height
        self.height = msg_label.texture_size[1] + dp(40)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class MemoryCard(BoxLayout):
    """Memory display card"""
    title = StringProperty('')
    content = StringProperty('')
    memory_id = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(120)
        self.padding = dp(12)
        self.spacing = dp(8)
        
        # Background
        with self.canvas.before:
            Color(*COLORS['surface'])
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Title
        title_label = Label(
            text=self.title,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(24),
            font_size=sp(16),
            bold=True,
            halign='left',
            valign='top'
        )
        self.add_widget(title_label)
        
        # Content preview
        content_label = Label(
            text=self.content[:100] + '...' if len(self.content) > 100 else self.content,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(48),
            font_size=sp(14),
            halign='left',
            valign='top',
            text_size=(self.width - dp(24), None)
        )
        self.add_widget(content_label)
        
        # Action buttons
        btn_layout = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        
        edit_btn = Button(
            text='Edit',
            size_hint_x=0.5,
            background_color=COLORS['primary'],
            on_press=lambda x: self.on_edit()
        )
        delete_btn = Button(
            text='Delete',
            size_hint_x=0.5,
            background_color=COLORS['error'],
            on_press=lambda x: self.on_delete()
        )
        
        btn_layout.add_widget(edit_btn)
        btn_layout.add_widget(delete_btn)
        self.add_widget(btn_layout)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def on_edit(self):
        # Handle edit action
        App.get_running_app().root.current_screen.edit_memory(self.memory_id)
    
    def on_delete(self):
        # Handle delete action
        App.get_running_app().root.current_screen.delete_memory(self.memory_id)


# ===========================================================================
# SCREENS
# ===========================================================================

class LoginScreen(Screen):
    """User login/registration screen"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_manager = UserManager()
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=dp(32), spacing=dp(16))
        
        # Background color
        with main_layout.canvas.before:
            Color(*COLORS['background'])
            self.bg_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)
        main_layout.bind(pos=self.update_bg, size=self.update_bg)
        
        # Logo/Title
        title = Label(
            text='[b]PSA Mobile[/b]\nPersonal Smart Assistant',
            markup=True,
            color=COLORS['primary'],
            font_size=sp(28),
            size_hint_y=None,
            height=dp(100),
            halign='center'
        )
        main_layout.add_widget(title)
        
        # Spacer
        main_layout.add_widget(Label(size_hint_y=0.3))
        
        # Username input
        self.username_input = TextInput(
            hint_text='Username',
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16),
            padding=[dp(16), dp(12)]
        )
        main_layout.add_widget(self.username_input)
        
        # Password input
        self.password_input = TextInput(
            hint_text='Password',
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16),
            padding=[dp(16), dp(12)]
        )
        main_layout.add_widget(self.password_input)
        
        # Login button
        login_btn = RoundedButton(
            text='Login',
            on_press=self.do_login
        )
        main_layout.add_widget(login_btn)
        
        # Register button
        register_btn = Button(
            text='Create Account',
            size_hint_y=None,
            height=dp(48),
            background_color=(0, 0, 0, 0),
            color=COLORS['primary'],
            on_press=self.do_register
        )
        main_layout.add_widget(register_btn)
        
        # Spacer
        main_layout.add_widget(Label(size_hint_y=0.5))
        
        self.add_widget(main_layout)
    
    def update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
    
    def do_login(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text
        
        if not username or not password:
            self.show_error('Please enter username and password')
            return
        
        if self.user_manager.verify_user(username, password):
            # Login successful
            self.manager.current = 'main'
        else:
            self.show_error('Invalid username or password')
    
    def do_register(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text
        
        if not username or not password:
            self.show_error('Please enter username and password')
            return
        
        if self.user_manager.create_user(username, password):
            self.show_success('Account created! Please login.')
            self.username_input.text = ''
            self.password_input.text = ''
        else:
            self.show_error('Username already exists')
    
    def show_error(self, message):
        popup = Popup(
            title='Error',
            content=Label(text=message),
            size_hint=(0.8, 0.3)
        )
        popup.open()
    
    def show_success(self, message):
        popup = Popup(
            title='Success',
            content=Label(text=message),
            size_hint=(0.8, 0.3)
        )
        popup.open()


class ChatScreen(Screen):
    """Main chat interface"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize backend
        self.backend = PSABackendBridge()
        self.current_conversation = None
        self.is_streaming = False
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical')
        
        # Top bar
        top_bar = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8), spacing=dp(8))
        top_bar.canvas.before.clear()
        with top_bar.canvas.before:
            Color(*COLORS['primary'])
            Rectangle(pos=top_bar.pos, size=top_bar.size)
        
        menu_btn = Button(
            text='☰',
            size_hint_x=None,
            width=dp(48),
            background_color=(0, 0, 0, 0),
            color=COLORS['surface'],
            font_size=sp(24),
            on_press=self.toggle_menu
        )
        top_bar.add_widget(menu_btn)
        
        title = Label(
            text='PSA Chat',
            color=COLORS['surface'],
            font_size=sp(20),
            bold=True
        )
        top_bar.add_widget(title)
        
        new_chat_btn = Button(
            text='+',
            size_hint_x=None,
            width=dp(48),
            background_color=(0, 0, 0, 0),
            color=COLORS['surface'],
            font_size=sp(24),
            on_press=self.new_conversation
        )
        top_bar.add_widget(new_chat_btn)
        
        main_layout.add_widget(top_bar)
        
        # Chat messages area
        self.messages_scroll = ScrollView(do_scroll_x=False)
        self.messages_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=dp(12)
        )
        self.messages_layout.bind(minimum_height=self.messages_layout.setter('height'))
        self.messages_scroll.add_widget(self.messages_layout)
        main_layout.add_widget(self.messages_scroll)
        
        # Input area
        input_layout = BoxLayout(size_hint_y=None, height=dp(64), padding=dp(8), spacing=dp(8))
        
        self.input_field = TextInput(
            hint_text='Type your message...',
            multiline=True,
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16)
        )
        input_layout.add_widget(self.input_field)
        
        send_btn = Button(
            text='➤',
            size_hint_x=None,
            width=dp(56),
            background_color=COLORS['primary'],
            font_size=sp(20),
            on_press=self.send_message
        )
        input_layout.add_widget(send_btn)
        
        main_layout.add_widget(input_layout)
        
        self.add_widget(main_layout)
        
        # Load initial conversation
        Clock.schedule_once(lambda dt: self.load_current_conversation(), 0.5)
    
    def toggle_menu(self, instance):
        # Navigate to menu/settings
        self.manager.current = 'menu'
    
    def new_conversation(self, instance):
        self.current_conversation = None
        self.messages_layout.clear_widgets()
    
    def load_current_conversation(self):
        """Load messages from current conversation"""
        user = get_current_user()
        if not user:
            return
        
        # Get or create conversation
        conv = get_conversation(user['username'], None)
        if conv:
            self.current_conversation = conv['conversation_id']
            
            # Load messages
            for msg in conv.get('messages', []):
                self.add_message_bubble(
                    msg['content'],
                    msg['role'] == 'user',
                    msg.get('timestamp', '')
                )
    
    def add_message_bubble(self, text, is_user, timestamp=''):
        """Add a message bubble to the chat"""
        if not timestamp:
            timestamp = datetime.now().strftime('%I:%M %p')
        
        bubble = MessageBubble(
            text=text,
            is_user=is_user,
            timestamp=timestamp
        )
        self.messages_layout.add_widget(bubble)
        
        # Scroll to bottom
        Clock.schedule_once(lambda dt: setattr(self.messages_scroll, 'scroll_y', 0), 0.1)
    
    def send_message(self, instance):
        """Send user message and get AI response"""
        user_message = self.input_field.text.strip()
        if not user_message:
            return
        
        # Clear input
        self.input_field.text = ''
        
        # Add user message
        self.add_message_bubble(user_message, True)
        
        # Save message
        user = get_current_user()
        if user and self.current_conversation:
            add_message(self.current_conversation, 'user', user_message)
        
        # Get AI response in background thread
        threading.Thread(target=self.get_ai_response, args=(user_message,), daemon=True).start()
    
    def get_ai_response(self, user_message):
        """Get AI response (runs in background thread)"""
        try:
            # Get response from backend
            response = self.backend.send_message(user_message, self.current_conversation)
            
            # Add AI response on main thread
            Clock.schedule_once(lambda dt: self.add_message_bubble(response, False), 0)
            
            # Save AI message
            user = get_current_user()
            if user and self.current_conversation:
                add_message(self.current_conversation, 'assistant', response)
        
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            Clock.schedule_once(lambda dt: self.add_message_bubble(error_msg, False), 0)


class MemoryScreen(Screen):
    """Memory management screen"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.memory_db = FileMemoryDB()
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical')
        
        # Top bar
        top_bar = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8), spacing=dp(8))
        with top_bar.canvas.before:
            Color(*COLORS['primary'])
            Rectangle(pos=top_bar.pos, size=top_bar.size)
        
        back_btn = Button(
            text='←',
            size_hint_x=None,
            width=dp(48),
            background_color=(0, 0, 0, 0),
            color=COLORS['surface'],
            font_size=sp(24),
            on_press=lambda x: setattr(self.manager, 'current', 'main')
        )
        top_bar.add_widget(back_btn)
        
        title = Label(
            text='Memories',
            color=COLORS['surface'],
            font_size=sp(20),
            bold=True
        )
        top_bar.add_widget(title)
        
        add_btn = Button(
            text='+',
            size_hint_x=None,
            width=dp(48),
            background_color=(0, 0, 0, 0),
            color=COLORS['surface'],
            font_size=sp(24),
            on_press=self.add_memory
        )
        top_bar.add_widget(add_btn)
        
        main_layout.add_widget(top_bar)
        
        # Search bar
        search_layout = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8))
        self.search_input = TextInput(
            hint_text='Search memories...',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        self.search_input.bind(text=self.on_search)
        search_layout.add_widget(self.search_input)
        main_layout.add_widget(search_layout)
        
        # Memories list
        self.memories_scroll = ScrollView()
        self.memories_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=dp(12)
        )
        self.memories_layout.bind(minimum_height=self.memories_layout.setter('height'))
        self.memories_scroll.add_widget(self.memories_layout)
        main_layout.add_widget(self.memories_scroll)
        
        self.add_widget(main_layout)
        
        # Load memories
        Clock.schedule_once(lambda dt: self.load_memories(), 0.5)
    
    def load_memories(self, search_query=''):
        """Load and display memories"""
        self.memories_layout.clear_widgets()
        
        user = get_current_user()
        if not user:
            return
        
        # Get memories from database
        memories = self.memory_db.search_memories(search_query) if search_query else self.memory_db.get_all_memories()
        
        for memory in memories:
            card = MemoryCard(
                title=memory.get('title', 'Untitled'),
                content=memory.get('content', ''),
                memory_id=str(memory.get('id', ''))
            )
            self.memories_layout.add_widget(card)
    
    def on_search(self, instance, value):
        """Handle search input"""
        Clock.unschedule(self.do_search)
        Clock.schedule_once(lambda dt: self.do_search(value), 0.5)
    
    def do_search(self, query):
        """Perform search"""
        self.load_memories(query)
    
    def add_memory(self, instance):
        """Show add memory dialog"""
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        title_input = TextInput(
            hint_text='Title',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title_input)
        
        content_input = TextInput(
            hint_text='Memory content...',
            size_hint_y=0.7
        )
        content.add_widget(content_input)
        
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        
        def save_memory(btn_instance):
            title = title_input.text.strip()
            memory_content = content_input.text.strip()
            
            if title and memory_content:
                user = get_current_user()
                if user:
                    self.memory_db.add_memory(
                        user['username'],
                        title,
                        memory_content
                    )
                    self.load_memories()
                    popup.dismiss()
        
        save_btn = Button(text='Save', on_press=save_memory)
        cancel_btn = Button(text='Cancel', on_press=lambda x: popup.dismiss())
        
        buttons.add_widget(cancel_btn)
        buttons.add_widget(save_btn)
        content.add_widget(buttons)
        
        popup = Popup(
            title='Add Memory',
            content=content,
            size_hint=(0.9, 0.7)
        )
        popup.open()
    
    def edit_memory(self, memory_id):
        """Edit existing memory"""
        # TODO: Implement edit dialog
        pass
    
    def delete_memory(self, memory_id):
        """Delete a memory"""
        self.memory_db.delete_memory(memory_id)
        self.load_memories()


class MenuScreen(Screen):
    """Settings and menu screen"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical')
        
        # Top bar
        top_bar = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8))
        with top_bar.canvas.before:
            Color(*COLORS['primary'])
            Rectangle(pos=top_bar.pos, size=top_bar.size)
        
        back_btn = Button(
            text='←',
            size_hint_x=None,
            width=dp(48),
            background_color=(0, 0, 0, 0),
            color=COLORS['surface'],
            font_size=sp(24),
            on_press=lambda x: setattr(self.manager, 'current', 'main')
        )
        top_bar.add_widget(back_btn)
        
        title = Label(
            text='Menu',
            color=COLORS['surface'],
            font_size=sp(20),
            bold=True
        )
        top_bar.add_widget(title)
        
        main_layout.add_widget(top_bar)
        
        # Menu items
        menu_scroll = ScrollView()
        menu_layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(16), spacing=dp(12))
        menu_layout.bind(minimum_height=menu_layout.setter('height'))
        
        # Menu buttons
        memories_btn = self.create_menu_item('💾 Memories', lambda: setattr(self.manager, 'current', 'memory'))
        reminders_btn = self.create_menu_item('⏰ Reminders', self.show_reminders)
        settings_btn = self.create_menu_item('⚙️ Settings', self.show_settings)
        about_btn = self.create_menu_item('ℹ️ About', self.show_about)
        logout_btn = self.create_menu_item('🚪 Logout', self.do_logout)
        
        menu_layout.add_widget(memories_btn)
        menu_layout.add_widget(reminders_btn)
        menu_layout.add_widget(settings_btn)
        menu_layout.add_widget(about_btn)
        menu_layout.add_widget(Label(size_hint_y=None, height=dp(32)))
        menu_layout.add_widget(logout_btn)
        
        menu_scroll.add_widget(menu_layout)
        main_layout.add_widget(menu_scroll)
        
        self.add_widget(main_layout)
    
    def create_menu_item(self, text, callback):
        """Create a menu button"""
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp(56),
            font_size=sp(16),
            halign='left',
            valign='middle',
            on_press=lambda x: callback() if callable(callback) else callback
        )
        btn.bind(size=lambda btn, size: setattr(btn, 'text_size', size))
        return btn
    
    def show_reminders(self):
        popup = Popup(
            title='Reminders',
            content=Label(text='Reminders feature coming soon!'),
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def show_settings(self):
        popup = Popup(
            title='Settings',
            content=Label(text='Settings feature coming soon!'),
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def show_about(self):
        about_text = '''PSA Mobile v1.0

Personal Smart Assistant

Powered by AI
Built with Python & Kivy

© 2024'''
        
        popup = Popup(
            title='About PSA',
            content=Label(text=about_text),
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def do_logout(self):
        # Clear user session
        self.manager.current = 'login'


# ===========================================================================
# MAIN APP
# ===========================================================================

class PSAMobileApp(App):
    """Main Kivy application"""
    
    def build(self):
        # Set window properties
        Window.clearcolor = COLORS['background']
        
        # Create screen manager
        sm = ScreenManager(transition=SlideTransition())
        
        # Add screens
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ChatScreen(name='main'))
        sm.add_widget(MemoryScreen(name='memory'))
        sm.add_widget(MenuScreen(name='menu'))
        
        # Start reminder service
        try:
            start_reminder_service()
        except Exception as e:
            print(f"Could not start reminder service: {e}")
        
        return sm
    
    def on_start(self):
        """Called when app starts"""
        print("PSA Mobile starting...")
    
    def on_stop(self):
        """Called when app closes"""
        print("PSA Mobile closing...")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == '__main__':
    PSAMobileApp().run()