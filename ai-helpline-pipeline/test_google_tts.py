"""
Quick test script to verify Google TTS integration without running the full pipeline.
This helps debug and validate the Google TTS client independently.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api_clients.google_tts_client import GoogleTTSClient
from config import AppConfig

def test_google_tts():
    """Test Google TTS client with various Indian languages."""
    
    print("=" * 60)
    print("Google Cloud TTS Test Script")
    print("=" * 60)
    
    # Load config
    try:
        config = AppConfig()
        if not config.google_tts_api_key:
            print("\n❌ ERROR: GOOGLE_TTS_API_KEY not found in environment variables!")
            print("Please add it to your .env file:")
            print("GOOGLE_TTS_API_KEY=your_api_key_here")
            return False
        print("\n✓ Config loaded successfully")
    except Exception as e:
        print(f"\n❌ Error loading config: {e}")
        return False
    
    # Initialize Google TTS client
    try:
        client = GoogleTTSClient(config)
        print("✓ Google TTS client initialized")
    except Exception as e:
        print(f"\n❌ Error initializing client: {e}")
        return False
    
    # Test cases for different languages
    test_cases = [
        ("en", "Hello farmer, this is a test of the Google Text to Speech system."),
        ("hi", "नमस्ते किसान भाई, यह गूगल टेक्स्ट टू स्पीच की परीक्षा है।"),
        ("ta", "வணக்கம் விவசாயி, இது கூகுள் டெக்ஸ்ட் டு ஸ்பீச் சோதனை ஆகும்."),
        ("te", "నమస్కారం రైతు, ఇది గూగుల్ టెక్స్ట్ టు స్పీచ్ పరీక్ష."),
        ("kn", "ನಮಸ್ಕಾರ ರೈತ, ಇದು ಗೂಗಲ್ ಟೆಕ್ಸ್ಟ್ ಟು ಸ್ಪೀಚ್ ಪರೀಕ್ಷೆ."),
    ]
    
    output_dir = Path("test_audio_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n{'='*60}")
    print("Testing TTS for multiple languages...")
    print(f"{'='*60}\n")
    
    success_count = 0
    for lang_code, text in test_cases:
        try:
            print(f"Testing {lang_code.upper()}...")
            print(f"  Text: {text[:50]}...")
            
            # Generate audio
            audio_bytes = client.text_to_speech(text, lang_code)
            
            # Save to file
            output_file = output_dir / f"test_{lang_code}.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_bytes)
            
            print(f"  ✓ Generated {len(audio_bytes):,} bytes")
            print(f"  ✓ Saved to: {output_file}")
            success_count += 1
            print()
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            print()
            continue
    
    print(f"{'='*60}")
    print(f"Test Results: {success_count}/{len(test_cases)} languages successful")
    print(f"{'='*60}")
    
    if success_count == len(test_cases):
        print("\n🎉 All tests passed! Google TTS is working correctly.")
        print(f"Audio files saved in: {output_dir.absolute()}")
        return True
    elif success_count > 0:
        print(f"\n⚠️  Partial success: {success_count} languages working")
        return True
    else:
        print("\n❌ All tests failed. Check your API key and network connection.")
        return False

if __name__ == "__main__":
    success = test_google_tts()
    sys.exit(0 if success else 1)
