import time
import base64
from typing import Optional

import requests

try:
    from ..config import AppConfig
except ImportError:
    from config import AppConfig


DEFAULT_TIMEOUT = 30


class GoogleTTSClient:
    """Google Cloud Text-to-Speech client using WaveNet voices for Indian languages."""
    
    # WaveNet voice mapping for Indian languages
    # Using female voices by default (can be made configurable)
    VOICE_MAP = {
        "hi": "hi-IN-Wavenet-D",      # Hindi - Female
        "ta": "ta-IN-Wavenet-A",      # Tamil - Female
        "te": "te-IN-Standard-A",     # Telugu - Female (WaveNet not available, using Standard)
        "kn": "kn-IN-Wavenet-A",      # Kannada - Female
        "ml": "ml-IN-Wavenet-A",      # Malayalam - Female
        "bn": "bn-IN-Wavenet-A",      # Bengali - Female
        "gu": "gu-IN-Wavenet-A",      # Gujarati - Female
        "mr": "mr-IN-Wavenet-A",      # Marathi - Female
        "pa": "pa-IN-Wavenet-A",      # Punjabi - Female
        "en": "en-IN-Wavenet-D",      # English (India) - Female
        "or": "or-IN-Standard-A",     # Odia - Female (WaveNet not available)
    }
    
    def __init__(self, config: AppConfig):
        self._api_key = config.google_tts_api_key
        self._base_url = config.endpoints.google_tts_base_url.rstrip("/")
        self._rate_per_min = config.rate_limits.tts_per_minute
        self._last_ts: float = 0.0
    
    def _throttle(self) -> None:
        """Rate limiting to avoid hitting API limits."""
        if self._rate_per_min <= 0:
            return
        interval = 60.0 / float(self._rate_per_min)
        delta = time.time() - self._last_ts
        if delta < interval:
            time.sleep(interval - delta)
        self._last_ts = time.time()
    
    def text_to_speech(self, text: str, target_lang: str) -> bytes:
        """
        Convert text to speech using Google Cloud TTS with WaveNet voices.
        
        Args:
            text: The text to convert to speech
            target_lang: Language code (hi, ta, te, kn, ml, bn, gu, mr, pa, en, or)
            
        Returns:
            Audio bytes in MP3 format
            
        Raises:
            RuntimeError: If TTS conversion fails
        """
        self._throttle()
        
        # Get the appropriate WaveNet voice for the language
        voice_name = self.VOICE_MAP.get(target_lang, "hi-IN-Wavenet-D")  # Default to Hindi
        
        # Construct the API URL
        url = f"{self._base_url}/text:synthesize?key={self._api_key}"
        
        # Build the request payload
        # Reference: https://cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize
        payload = {
            "input": {
                "text": text
            },
            "voice": {
                "languageCode": f"{target_lang}-IN",
                "name": voice_name
            },
            "audioConfig": {
                "audioEncoding": "MP3",  # MP3 format for compatibility with Twilio
                "speakingRate": 1.0,      # Normal speaking rate
                "pitch": 0.0,             # Normal pitch
                "volumeGainDb": 0.0       # Normal volume
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            
            # Handle errors
            if resp.status_code != 200:
                print("\n[Google TTS API Error]")
                print(f"Status code: {resp.status_code}")
                try:
                    error_data = resp.json()
                    print(f"Response: {error_data}")
                except Exception:
                    print(f"Raw response: {resp.text}")
                print(f"Request payload: {payload}")
                print(f"Voice used: {voice_name}")
            
            resp.raise_for_status()
            
        except requests.exceptions.HTTPError as e:
            print(f"\n[Google TTS Error] Failed to generate speech for language '{target_lang}'")
            raise RuntimeError(f"Google TTS API error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"\n[Google TTS Error] Network error: {e}")
            raise RuntimeError(f"Google TTS network error: {e}")
        
        # Parse the response
        data = resp.json()
        
        # The audio content is base64-encoded in the response
        audio_content_b64 = data.get("audioContent")
        if not audio_content_b64:
            raise RuntimeError("Google TTS returned no audio content")
        
        # Decode base64 to get raw audio bytes
        audio_bytes = base64.b64decode(audio_content_b64)
        
        return audio_bytes
