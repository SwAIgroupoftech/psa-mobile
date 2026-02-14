"""
Voice Input for PSA
Record voice -> Transcribe -> Send to chat
Uses Google Speech Recognition (free, works offline)
"""

import os
import tempfile
from typing import Optional

# Speech recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    print("⚠️ speech_recognition not installed. Install: pip install SpeechRecognition pyaudio")


class VoiceInput:
    """Voice input handler using Google Speech Recognition"""
    
    def __init__(self):
        """Initialize voice input"""
        if not SPEECH_AVAILABLE:
            raise RuntimeError("Speech recognition not available")
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300  # Adjust for ambient noise
        self.recognizer.dynamic_energy_threshold = True
    
    def transcribe_from_microphone(self, duration=5, language='en-US') -> Optional[str]:
        """
        Record from microphone and transcribe.
        
        Args:
            duration: Recording duration in seconds (or until silence)
            language: Language code ('en-US', 'hi-IN', 'te-IN', etc.)
        
        Returns:
            Transcribed text or None
        """
        try:
            with sr.Microphone() as source:
                print("🎤 Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                print(f"🎤 Listening... (speak now, max {duration}s)")
                audio = self.recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
                
                print("🔄 Transcribing...")
                text = self.recognizer.recognize_google(audio, language=language)
                
                print(f"✅ Transcribed: {text}")
                return text
        
        except sr.WaitTimeoutError:
            print("⏱️ No speech detected")
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech API error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def test_microphone(self) -> bool:
        """Test if microphone is working"""
        try:
            with sr.Microphone() as source:
                print("🎤 Microphone test...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("✅ Microphone is working!")
                return True
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            return False


# Simple API for main.py
def quick_voice_input(duration=5, language='en-US') -> Optional[str]:
    """
    Quick voice input function.
    
    Args:
        duration: Recording duration in seconds
        language: Language code
    
    Returns:
        Transcribed text or None
    
    Example:
        text = quick_voice_input(duration=5, language='en-US')
        if text:
            print(f"You said: {text}")
    """
    try:
        voice = VoiceInput()
        return voice.transcribe_from_microphone(duration, language)
    except Exception as e:
        print(f"❌ Voice input error: {e}")
        return None


# Testing
if __name__ == "__main__":
    print("\n🎤 PSA Voice Input Test\n")
    
    if not SPEECH_AVAILABLE:
        print("❌ speech_recognition not installed")
        print("📦 Install: pip install SpeechRecognition pyaudio")
        exit(1)
    
    voice = VoiceInput()
    
    # Test microphone
    if not voice.test_microphone():
        print("\n❌ Microphone not working!")
        print("💡 Make sure:")
        print("  1. Microphone is connected")
        print("  2. Microphone permissions are granted")
        print("  3. PyAudio is installed: pip install pyaudio")
        exit(1)
    
    # Test transcription
    print("\n" + "="*60)
    print("🎤 Say something...")
    text = quick_voice_input(duration=5)
    
    if text:
        print(f"\n✅ SUCCESS! You said: '{text}'")
    else:
        print("\n❌ Failed to transcribe")
    
    print("="*60)