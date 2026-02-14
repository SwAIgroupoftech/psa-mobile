"""
multilingual_tts.py - Multi-language TTS with 15+ language support
Supports Hindi, Telugu, Tamil, and many more with auto-detection
"""

import re
import os
import tempfile
import threading
from typing import Optional, Literal

# Suppress Qt warnings
os.environ['QT_LOGGING_RULES'] = 'qt.text.font.db=false;qt.qpa.fonts=false'

# TTS Engine
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ gTTS not installed. Run: pip install gtts")

# Audio Player
try:
    import pygame
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ pygame not installed. Run: pip install pygame")


# ===========================================================================
#   LANGUAGE DETECTION & VOICE MAPPING
# ===========================================================================

# Comprehensive language support
LANGUAGE_CODES = {
    # Indian Languages
    'hindi': 'hi',
    'telugu': 'te',
    'tamil': 'ta',
    'kannada': 'kn',
    'malayalam': 'ml',
    'bengali': 'bn',
    'gujarati': 'gu',
    'marathi': 'mr',
    'punjabi': 'pa',
    'urdu': 'ur',
    
    # Major World Languages
    'english': 'en',
    'spanish': 'es',
    'french': 'fr',
    'german': 'de',
    'italian': 'it',
    'portuguese': 'pt',
    'russian': 'ru',
    'japanese': 'ja',
    'korean': 'ko',
    'chinese': 'zh-CN',
    'arabic': 'ar',
    'turkish': 'tr',
    'dutch': 'nl',
    'polish': 'pl',
    'swedish': 'sv',
    'thai': 'th',
    'vietnamese': 'vi',
    'indonesian': 'id',
}

# Regional accents for better pronunciation
LANGUAGE_ACCENTS = {
    'en': 'com',      # English - US
    'hi': 'co.in',    # Hindi - India
    'te': 'co.in',    # Telugu - India
    'ta': 'co.in',    # Tamil - India
    'kn': 'co.in',    # Kannada - India
    'ml': 'co.in',    # Malayalam - India
    'bn': 'co.in',    # Bengali - India
    'gu': 'co.in',    # Gujarati - India
    'mr': 'co.in',    # Marathi - India
    'pa': 'co.in',    # Punjabi - India
    'ur': 'co.in',    # Urdu - India
    'es': 'es',       # Spanish - Spain
    'fr': 'fr',       # French - France
    'de': 'de',       # German - Germany
    'pt': 'com.br',   # Portuguese - Brazil
    'ja': 'co.jp',    # Japanese - Japan
    'ko': 'co.kr',    # Korean - Korea
    'zh-CN': 'com',   # Chinese - Mainland
}


def detect_language_from_text(text: str) -> str:
    """
    Auto-detect language from text based on Unicode ranges.
    
    Returns:
        Language code (e.g., 'hi', 'te', 'en')
    """
    # Remove markdown, emojis, code blocks
    clean_text = clean_text_for_speech(text)
    
    # Devanagari (Hindi, Marathi, Sanskrit)
    if re.search(r'[\u0900-\u097F]', clean_text):
        # Check if more Marathi-specific characters
        if re.search(r'[\u0966-\u096F]', clean_text):
            return 'mr'
        return 'hi'
    
    # Telugu
    if re.search(r'[\u0C00-\u0C7F]', clean_text):
        return 'te'
    
    # Tamil
    if re.search(r'[\u0B80-\u0BFF]', clean_text):
        return 'ta'
    
    # Kannada
    if re.search(r'[\u0C80-\u0CFF]', clean_text):
        return 'kn'
    
    # Malayalam
    if re.search(r'[\u0D00-\u0D7F]', clean_text):
        return 'ml'
    
    # Bengali
    if re.search(r'[\u0980-\u09FF]', clean_text):
        return 'bn'
    
    # Gujarati
    if re.search(r'[\u0A80-\u0AFF]', clean_text):
        return 'gu'
    
    # Punjabi (Gurmukhi)
    if re.search(r'[\u0A00-\u0A7F]', clean_text):
        return 'pa'
    
    # Japanese (Hiragana, Katakana, Kanji)
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', clean_text):
        return 'ja'
    
    # Korean (Hangul)
    if re.search(r'[\uAC00-\uD7AF]', clean_text):
        return 'ko'
    
    # Chinese (CJK Unified Ideographs)
    if re.search(r'[\u4E00-\u9FFF]', clean_text):
        return 'zh-CN'
    
    # Arabic
    if re.search(r'[\u0600-\u06FF]', clean_text):
        return 'ar'
    
    # Thai
    if re.search(r'[\u0E00-\u0E7F]', clean_text):
        return 'th'
    
    # Default to English
    return 'en'


def clean_text_for_speech(text: str) -> str:
    """Clean text for TTS (remove markdown, emojis, code, etc.)."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    
    # Remove markdown formatting
    text = re.sub(r'[#*_~`]', '', text)
    
    # Remove emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# ===========================================================================
#   AUDIO PLAYER
# ===========================================================================

class AudioPlayer:
    """Simple audio player using pygame."""
    
    @staticmethod
    def play(file_path: str, blocking: bool = True):
        """Play audio file."""
        if not AUDIO_AVAILABLE:
            print("❌ Audio player not available")
            return False
        
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            if blocking:
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            
            return True
        except Exception as e:
            print(f"❌ Playback error: {e}")
            return False
    
    @staticmethod
    def stop():
        """Stop current playback."""
        try:
            pygame.mixer.music.stop()
        except:
            pass


# ===========================================================================
#   MULTI-LANGUAGE TTS
# ===========================================================================

class MultilingualTTS:
    """Advanced multi-language text-to-speech."""
    
    def __init__(self):
        """Initialize TTS system."""
        self.player = AudioPlayer()
        
        if not TTS_AVAILABLE:
            raise RuntimeError("gTTS not installed. Run: pip install gtts")
    
    def speak(
        self,
        text: str,
        lang: Optional[str] = None,
        auto_detect: bool = True,
        speed: Literal['slow', 'normal'] = 'normal',
        blocking: bool = True
    ) -> bool:
        """
        Speak text in detected or specified language.
        
        Args:
            text: Text to speak
            lang: Language code (None = auto-detect)
            auto_detect: Auto-detect language if lang not provided
            speed: 'slow' or 'normal'
            blocking: Wait for speech to finish
        
        Returns:
            True if successful
        """
        # Clean text
        cleaned_text = clean_text_for_speech(text)
        
        if not cleaned_text.strip():
            print("⚠️ No readable text after cleaning")
            return False
        
        # Detect or use provided language
        if lang is None and auto_detect:
            lang = detect_language_from_text(cleaned_text)
            lang_name = self._get_language_name(lang)
            print(f"🗣️ Speaking in: {lang_name}")
        elif lang is None:
            lang = 'en'
        
        # Get accent for natural pronunciation
        tld = LANGUAGE_ACCENTS.get(lang, 'com')
        
        try:
            # Create TTS
            tts = gTTS(
                text=cleaned_text,
                lang=lang,
                tld=tld,
                slow=(speed == 'slow')
            )
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_path = temp_file.name
            temp_file.close()
            
            tts.save(temp_path)
            
            # Play audio
            success = self.player.play(temp_path, blocking=blocking)
            
            # Cleanup
            if blocking:
                try:
                    os.unlink(temp_path)
                except:
                    pass
            else:
                # Cleanup after 10 seconds in background
                def delayed_cleanup():
                    import time
                    time.sleep(10)
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                threading.Thread(target=delayed_cleanup, daemon=True).start()
            
            return success
            
        except Exception as e:
            print(f"❌ TTS error: {e}")
            return False
    
    def speak_in_language(
        self,
        text: str,
        language_name: str,
        blocking: bool = True
    ) -> bool:
        """
        Speak text in specific language by name.
        
        Args:
            text: Text to speak
            language_name: Language name (e.g., 'hindi', 'telugu', 'tamil')
            blocking: Wait for completion
        
        Returns:
            True if successful
        """
        lang_code = LANGUAGE_CODES.get(language_name.lower())
        
        if not lang_code:
            print(f"❌ Unsupported language: {language_name}")
            print(f"Supported: {', '.join(LANGUAGE_CODES.keys())}")
            return False
        
        return self.speak(text, lang=lang_code, auto_detect=False, blocking=blocking)
    
    def stop(self):
        """Stop current speech."""
        self.player.stop()
    
    def _get_language_name(self, lang_code: str) -> str:
        """Get language name from code."""
        for name, code in LANGUAGE_CODES.items():
            if code == lang_code:
                return name.title()
        return lang_code.upper()
    
    @staticmethod
    def list_supported_languages() -> list:
        """Get list of all supported languages."""
        return sorted(LANGUAGE_CODES.keys())


# ===========================================================================
#   SIMPLE API FOR MAIN.PY
# ===========================================================================

def speak(
    text: str,
    lang: Optional[str] = None,
    blocking: bool = False
) -> bool:
    """
    Simple function to speak text (auto-detects language).
    
    Args:
        text: Text to speak
        lang: Language code (None = auto-detect)
        blocking: Wait for speech to finish
    
    Returns:
        True if successful
    """
    try:
        tts = MultilingualTTS()
        return tts.speak(text, lang=lang, auto_detect=True, blocking=blocking)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return False


def speak_in_language(text: str, language: str, blocking: bool = False) -> bool:
    """
    Speak text in specific language.
    
    Args:
        text: Text to speak
        language: Language name ('hindi', 'telugu', 'english', etc.)
        blocking: Wait for completion
    
    Returns:
        True if successful
    """
    try:
        tts = MultilingualTTS()
        return tts.speak_in_language(text, language, blocking)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return False


# ===========================================================================
#   TESTING
# ===========================================================================

if __name__ == "__main__":
    print("\n🗣️ Multi-Language TTS Test\n")
    print("=" * 60)
    
    # Test language detection and speech
    test_texts = {
        'English': "Hello! This is a test of the text to speech system.",
        'Hindi': "नमस्ते! मैं PSA हूं।",
        'Telugu': "హలో! నేను PSA.",
        'Tamil': "வணக்கம்! நான் PSA.",
        'Spanish': "¡Hola! Soy PSA.",
        'French': "Bonjour! Je suis PSA.",
    }
    
    print("\nSupported Languages:")
    print(", ".join(MultilingualTTS.list_supported_languages()))
    print("\n" + "=" * 60)
    
    tts = MultilingualTTS()
    
    for lang_name, text in test_texts.items():
        print(f"\n🗣️ Testing {lang_name}:")
        print(f"   Text: {text}")
        detected = detect_language_from_text(text)
        print(f"   Detected: {detected}")
        
        # Uncomment to actually play audio:
        # tts.speak(text, blocking=True)
    
    print("\n✅ Test complete!")