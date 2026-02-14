"""
PSA Vision & File Upload System - FIXED
========================================
No circular imports, clean architecture

Features:
- 📸 Image analysis using Google Gemini Vision (FREE)
- 📄 Document processing (PDF, DOCX, TXT)
- 🔍 Automatic file type detection
- 💾 PSA personality integration
"""

import os
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
import io

# ===========================================================================
#   CHECK AVAILABLE LIBRARIES
# ===========================================================================

VISION_APIS = {}

# Google Gemini Vision (FREE)
try:
    import google.generativeai as genai
    from PIL import Image
    VISION_APIS['gemini'] = True
except ImportError:
    VISION_APIS['gemini'] = False

# OpenAI GPT-4 Vision (Paid)
try:
    from openai import OpenAI
    VISION_APIS['openai'] = True
except ImportError:
    VISION_APIS['openai'] = False

# Document processing
DOC_SUPPORT = {}

try:
    import PyPDF2
    DOC_SUPPORT['pdf'] = True
except ImportError:
    DOC_SUPPORT['pdf'] = False

try:
    from docx import Document
    DOC_SUPPORT['docx'] = True
except ImportError:
    DOC_SUPPORT['docx'] = False


# ===========================================================================
#   FILE TYPE DETECTION
# ===========================================================================

def get_file_type(file_path: str) -> str:
    """Detect file type from path"""
    ext = Path(file_path).suffix.lower()
    
    image_types = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
    doc_types = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'}
    
    if ext in image_types:
        return 'image'
    elif ext in doc_types:
        return 'document'
    else:
        return 'unknown'


def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


# ===========================================================================
#   DOCUMENT PROCESSING
# ===========================================================================

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF file"""
    if not DOC_SUPPORT.get('pdf'):
        return "Error: PDF support not installed. Run: pip install PyPDF2"
    
    try:
        text = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        
        return '\n\n'.join(text) if text else "No text found in PDF"
    except Exception as e:
        return f"Error extracting PDF: {e}"


def extract_docx_text(docx_path: str) -> str:
    """Extract text from DOCX file"""
    if not DOC_SUPPORT.get('docx'):
        return "Error: DOCX support not installed. Run: pip install python-docx"
    
    try:
        doc = Document(docx_path)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        
        return '\n'.join(text) if text else "No text found in document"
    except Exception as e:
        return f"Error extracting DOCX: {e}"


def extract_text_file(file_path: str) -> str:
    """Extract text from plain text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try different encodings
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def extract_document_content(file_path: str) -> str:
    """Extract text content from any supported document"""
    ext = Path(file_path).suffix.lower()
    
    if ext == '.pdf':
        return extract_pdf_text(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_docx_text(file_path)
    elif ext in ['.txt', '.md', '.rtf']:
        return extract_text_file(file_path)
    else:
        return f"Unsupported document format: {ext}"


# ===========================================================================
#   VISION ANALYZER
# ===========================================================================

class VisionAnalyzer:
    """Analyze images using Google Gemini Vision"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize vision analyzer with Google Gemini.
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
        """
        if not VISION_APIS.get('gemini'):
            raise RuntimeError(
                "Google Gemini not installed.\n"
                "Install with: pip install google-generativeai pillow"
            )
        
        # Configure Gemini
        api_key = "AIzaSyD3rcef9HlAtZgmDSQIgZ_Bykrlvj9DLsA"
        if not api_key:
            raise RuntimeError(
                "Google API key not found.\n"
                "Set GOOGLE_API_KEY environment variable or pass api_key parameter.\n"
                "Get free key at: https://makersuite.google.com/app/apikey"
            )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def analyze_image(self, 
                      image_path: str, 
                      prompt: str = "Describe this image in detail.",
                      max_tokens: int = 500) -> str:
        """
        Analyze an image using Google Gemini Vision.
        
        Args:
            image_path: Path to image file
            prompt: Question/prompt about the image
            max_tokens: Maximum response length
        
        Returns:
            Analysis text
        """
        try:
            # Load image
            img = Image.open(image_path)
            
            # Generate content
            response = self.model.generate_content([prompt, img])
            
            return response.text
            
        except Exception as e:
            return f"❌ Vision analysis error: {e}"


# ===========================================================================
#   PSA PERSONALITY INTEGRATION
# ===========================================================================

def analyze_file_with_psa_personality(
    username: str,
    user_memory: Dict,
    file_path: str,
    user_message: str,
    conv_id: str,
    recent_context: str = ""
) -> str:
    """
    Analyze file with PSA's personality and memory integration.
    
    Args:
        username: Current user
        user_memory: User's memory dict (likes, hobbies, etc.)
        file_path: Path to uploaded file
        user_message: User's question/message
        conv_id: Current conversation ID
        recent_context: Recent conversation context
    
    Returns:
        Personalized response from PSA
    """
    file_name = Path(file_path).name
    file_type = get_file_type(file_path)
    
    # Build personalized response
    response_parts = []
    
    # 1. Friendly greeting
    response_parts.append(f"Got it! Looking at your {file_type}... 👀")
    
    # 2. Process the file
    try:
        if file_type == 'image':
            analysis = _analyze_image_with_memory(
                file_path,
                user_message,
                user_memory,
                recent_context
            )
        elif file_type == 'document':
            analysis = _analyze_document_with_memory(
                file_path,
                user_message,
                user_memory,
                recent_context
            )
        else:
            analysis = f"I can see this is a {file_type} file, but I'm not sure how to analyze it yet. 🤔"
        
        response_parts.append(analysis)
        
    except Exception as e:
        response_parts.append(f"Oops! I had trouble analyzing that file. Error: {e}")
    
    # 3. Connect to memory if relevant
    memory_connection = _connect_to_memory(response_parts[-1], user_memory)
    if memory_connection:
        response_parts.append(memory_connection)
    
    return "\n\n".join(response_parts)


def _analyze_image_with_memory(
    image_path: str,
    user_prompt: Optional[str],
    user_memory: Dict,
    recent_context: str
) -> str:
    """Analyze image with PSA personality using Cerebras + Gemini"""
    
    # Step 1: Get image description from Gemini
    try:
        vision = VisionAnalyzer()
        
        basic_prompt = (
            "Describe this image in detail. Include: objects, people, text visible, "
            "colors, setting, activities, emotions. Be factual and detailed."
        )
        
        image_description = vision.analyze_image(image_path, basic_prompt)
        
    except Exception as e:
        return f"Hmm, I had trouble analyzing this image. Error: {e}\n\nMake sure you have:\n1. Installed: pip install google-generativeai pillow\n2. Set GOOGLE_API_KEY environment variable"
    
    # Step 2: Use Cerebras to generate PSA's personalized response
    memory_context = _build_memory_context(user_memory)
    
    cerebras_prompt = f"""You are PSA, a personal assistant. Respond to this image with warmth and personality!

IMAGE DESCRIPTION (from vision AI):
{image_description}

WHAT YOU KNOW ABOUT THE USER:
{memory_context}

RECENT CONVERSATION:
{recent_context[:500] if recent_context else "First message in conversation"}

USER'S QUESTION: {user_prompt or "What do you think about this image?"}

YOUR TASK:
1. Respond in a friendly, warm way based on the image description
2. Connect the image to what you know about them (hobbies, interests, goals)
3. Ask engaging follow-up questions
4. Be conversational and use emojis naturally (but don't overdo it)
5. Show you care about them

Remember: You're their helpful friend who knows them well!"""
    
    try:
        # Use Cerebras for intelligent response
        from cerebras.cloud.sdk import Cerebras
        from users import CEREBRAS_API_KEY
        
        client = Cerebras(api_key=CEREBRAS_API_KEY)
        response = client.chat.completions.create( model="gpt-oss-120b", messages=[{"role": "user", "content": cerebras_prompt}])
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Fallback to just description if Cerebras fails
        return f"Based on what I can see: {image_description}"


def _analyze_document_with_memory(
    doc_path: str,
    user_prompt: Optional[str],
    user_memory: Dict,
    recent_context: str
) -> str:
    """Analyze document with PSA personality"""
    
    # Extract document content
    content = extract_document_content(doc_path)
    
    if "Error" in content:
        return f"I had trouble reading this document: {content}"
    
    # Truncate if too long
    content_preview = content[:2000]
    if len(content) > 2000:
        content_preview += "\n\n[Document continues...]"
    
    # Build context
    memory_context = _build_memory_context(user_memory)
    
    # Use Cerebras for personalized response
    cerebras_prompt = f"""You are PSA, a personal assistant. Respond to this document with warmth!

DOCUMENT CONTENT:
{content_preview}

WHAT YOU KNOW ABOUT THE USER:
{memory_context}

RECENT CONVERSATION:
{recent_context[:500] if recent_context else "First message"}

USER'S QUESTION: {user_prompt or "What's in this document?"}

YOUR TASK:
1. Summarize the key points
2. Connect it to what you know about them
3. Be friendly and helpful
4. Ask if they want you to remember anything

Remember: You're their personal assistant!"""
    
    try:
        from cerebras.cloud.sdk import Cerebras
        from users import CEREBRAS_API_KEY
        
        client = Cerebras(api_key=CEREBRAS_API_KEY)
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[{"role": "user", "content": cerebras_prompt}],
            max_tokens=600,
            temperature=0.8
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Fallback
        return f"""Here's what I found in your document:

📄 **Content Preview:**
{content_preview}

💡 Want me to remember anything specific from this?"""


def _build_memory_context(user_memory: Dict) -> str:
    """Build memory summary"""
    context_parts = []
    
    if user_memory.get('name'):
        context_parts.append(f"Name: {', '.join(user_memory['name'])}")
    
    if user_memory.get('likes'):
        context_parts.append(f"Likes: {', '.join(user_memory['likes'][:3])}")
    
    if user_memory.get('hobbies'):
        context_parts.append(f"Hobbies: {', '.join(user_memory['hobbies'][:3])}")
    
    if user_memory.get('goals'):
        context_parts.append(f"Goals: {', '.join(user_memory['goals'][:2])}")
    
    return "\n".join(context_parts) if context_parts else "Just getting to know them!"


def _connect_to_memory(analysis: str, user_memory: Dict) -> Optional[str]:
    """Try to connect analysis to user's memory"""
    connections = []
    analysis_lower = analysis.lower()
    
    # Check hobbies
    for hobby in user_memory.get('hobbies', []):
        if hobby.lower() in analysis_lower:
            connections.append(f"🎯 This connects to your hobby: {hobby}!")
    
    # Check likes
    for like in user_memory.get('likes', []):
        if like.lower() in analysis_lower:
            connections.append(f"❤️ I see you're into {like} - nice!")
    
    if connections:
        return "\n".join(connections[:2])  # Max 2 connections
    
    return None


# ===========================================================================
#   SIMPLE API FOR MAIN.PY
# ===========================================================================

def quick_analyze_file(file_path: str, user_message: str = "") -> str:
    """
    Quick function for simple file analysis (no personality).
    
    Args:
        file_path: Path to file
        user_message: User's question
    
    Returns:
        Analysis text
    """
    file_type = get_file_type(file_path)
    
    if file_type == 'image':
        try:
            vision = VisionAnalyzer()
            return vision.analyze_image(file_path, user_message or "Describe this image.")
        except Exception as e:
            return f"Error: {e}"
    
    elif file_type == 'document':
        content = extract_document_content(file_path)
        return f"Document content:\n\n{content[:1000]}"
    
    else:
        return f"Unsupported file type: {Path(file_path).suffix}"


# ===========================================================================
#   TESTING
# ===========================================================================

if __name__ == "__main__":
    print("\n🔍 PSA Vision System Test\n")
    print("=" * 60)
    
    # Check APIs
    print("\n📦 Available Vision APIs:")
    for api, available in VISION_APIS.items():
        print(f"  {'✅' if available else '❌'} {api}")
    
    print("\n📄 Document Support:")
    for doc_type, available in DOC_SUPPORT.items():
        print(f"  {'✅' if available else '❌'} {doc_type}")
    
    print("\n" + "=" * 60)
    
    # Test instructions
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"\n🧪 Testing with: {test_file}\n")
        result = quick_analyze_file(test_file, "What can you tell me?")
        print(result)
    else:
        print("\n💡 To test:")
        print("   python vision_file_system.py <file_path>")
        print("\n   Examples:")
        print("   python vision_file_system.py photo.jpg")
        print("   python vision_file_system.py document.pdf")