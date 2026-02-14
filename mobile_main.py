"""
PSA Mobile - Minimal Standalone Version
This version works without desktop dependencies
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, BooleanProperty

import json
import os
from datetime import datetime

# Simple file-based storage
class SimpleStorage:
    def __init__(self):
        self.data_file = 'psa_data.json'
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = {'users': {}, 'conversations': {}}
        else:
            self.data = {'users': {}, 'conversations': {}}
    
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f)
    
    def create_user(self, username, password):
        if username in self.data['users']:
            return False
        self.data['users'][username] = {
            'password': password,
            'conversations': []
        }
        self.save_data()
        return True
    
    def verify_user(self, username, password):
        if username in self.data['users']:
            return self.data['users'][username]['password'] == password
        return False
    
    def add_message(self, username, role, content):
        if username not in self.data['conversations']:
            self.data['conversations'][username] = []
        self.data['conversations'][username].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        self.save_data()
    
    def get_messages(self, username):
        return self.data['conversations'].get(username, [])

# Colors
COLORS = {
    'primary': get_color_from_hex('#2196F3'),
    'surface': get_color_from_hex('#FFFFFF'),
    'background': get_color_from_hex('#FAFAFA'),
    'text_primary': get_color_from_hex('#212121'),
    'text_secondary': get_color_from_hex('#757575'),
    'user_bubble': get_color_from_hex('#E3F2FD'),
    'ai_bubble': get_color_from_hex('#F5F5F5'),
}

# Message Bubble Widget
class MessageBubble(BoxLayout):
    text = StringProperty('')
    is_user = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = dp(12)
        self.spacing = dp(4)
        
        if self.is_user:
            self.size_hint_x = 0.75
            self.pos_hint = {'right': 1}
            bg_color = COLORS['user_bubble']
        else:
            self.size_hint_x = 0.85
            self.pos_hint = {'x': 0}
            bg_color = COLORS['ai_bubble']
        
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        msg_label = Label(
            text=self.text,
            color=COLORS['text_primary'],
            size_hint_y=None,
            markup=True,
            text_size=(Window.width * 0.7, None),
            halign='left',
            valign='top',
            font_size=sp(15)
        )
        msg_label.bind(texture_size=lambda *x: msg_label.setter('height')(msg_label, msg_label.texture_size[1]))
        self.add_widget(msg_label)
        
        self.height = msg_label.texture_size[1] + dp(30)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# Login Screen
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.storage = App.get_running_app().storage
        
        main_layout = BoxLayout(orientation='vertical', padding=dp(32), spacing=dp(16))
        
        title = Label(
            text='[b]PSA Mobile[/b]\nPersonal Smart Assistant',
            markup=True,
            color=COLORS['primary'],
            font_size=sp(28),
            size_hint_y=None,
            height=dp(100)
        )
        main_layout.add_widget(title)
        main_layout.add_widget(Label(size_hint_y=0.3))
        
        self.username_input = TextInput(
            hint_text='Username',
            multiline=False,
            size_hint_y=None,
            height=dp(48)
        )
        main_layout.add_widget(self.username_input)
        
        self.password_input = TextInput(
            hint_text='Password',
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(48)
        )
        main_layout.add_widget(self.password_input)
        
        login_btn = Button(
            text='Login',
            size_hint_y=None,
            height=dp(48),
            background_color=COLORS['primary'],
            on_press=self.do_login
        )
        main_layout.add_widget(login_btn)
        
        register_btn = Button(
            text='Create Account',
            size_hint_y=None,
            height=dp(48),
            on_press=self.do_register
        )
        main_layout.add_widget(register_btn)
        
        main_layout.add_widget(Label(size_hint_y=0.5))
        self.add_widget(main_layout)
    
    def do_login(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text
        
        if self.storage.verify_user(username, password):
            App.get_running_app().current_user = username
            self.manager.current = 'chat'
        else:
            print("Invalid credentials")
    
    def do_register(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text
        
        if self.storage.create_user(username, password):
            print("Account created")
            self.username_input.text = ''
            self.password_input.text = ''

# Chat Screen
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical')
        
        # Top bar
        top_bar = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8))
        with top_bar.canvas.before:
            Color(*COLORS['primary'])
        
        title = Label(
            text='PSA Chat',
            color=COLORS['surface'],
            font_size=sp(20),
            bold=True
        )
        top_bar.add_widget(title)
        main_layout.add_widget(top_bar)
        
        # Messages area
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
            height=dp(48)
        )
        input_layout.add_widget(self.input_field)
        
        send_btn = Button(
            text='Send',
            size_hint_x=None,
            width=dp(80),
            background_color=COLORS['primary'],
            on_press=self.send_message
        )
        input_layout.add_widget(send_btn)
        
        main_layout.add_widget(input_layout)
        self.add_widget(main_layout)
    
    def on_enter(self):
        """Load messages when screen is entered"""
        self.messages_layout.clear_widgets()
        username = App.get_running_app().current_user
        messages = App.get_running_app().storage.get_messages(username)
        for msg in messages[-20:]:  # Show last 20 messages
            self.add_message_bubble(msg['content'], msg['role'] == 'user')
    
    def add_message_bubble(self, text, is_user):
        bubble = MessageBubble(text=text, is_user=is_user)
        self.messages_layout.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.messages_scroll, 'scroll_y', 0), 0.1)
    
    def send_message(self, instance):
        user_message = self.input_field.text.strip()
        if not user_message:
            return
        
        self.input_field.text = ''
        self.add_message_bubble(user_message, True)
        
        # Save user message
        username = App.get_running_app().current_user
        App.get_running_app().storage.add_message(username, 'user', user_message)
        
        # Simple echo response (replace with actual AI later)
        ai_response = f"Echo: {user_message}\n\n(AI integration coming soon!)"
        Clock.schedule_once(lambda dt: self.add_message_bubble(ai_response, False), 0.5)
        App.get_running_app().storage.add_message(username, 'assistant', ai_response)

# Main App
class PSAMobileApp(App):
    def build(self):
        self.storage = SimpleStorage()
        self.current_user = None
        
        Window.clearcolor = COLORS['background']
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ChatScreen(name='chat'))
        
        return sm

if __name__ == '__main__':
    PSAMobileApp().run()
