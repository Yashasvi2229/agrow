import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

try:
    from ..config import AppConfig
except ImportError:
    from config import AppConfig


DEFAULT_TIMEOUT = 60  # Increased timeout for potentially long audio files

@dataclass
class STTResult:
    text: str
    confidence: float
    language: str


class DeepgramClient:
    """
    Deepgram STT client with automatic language detection.
    Supports 36+ languages including Hindi, Tamil, Telugu, and code-switching.
    """
    def __init__(self, config: AppConfig):
        self._api_key = config.deepgram_api_key
        self._base_url = "https://api.deepgram.com/v1"
        self._rate_per_min = config.rate_limits.stt_per_minute
        self._last_ts: float = 0.0
        self._model = "nova-2"  # Nova-2 for multi-language support

    def _throttle(self) -> None:
        if self._rate_per_min <= 0:
            return
        interval = 60.0 / float(self._rate_per_min)
        delta = time.time() - self._last_ts
        if delta < interval:
            time.sleep(interval - delta)
        self._last_ts = time.time()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "audio/wav"
        }

    def speech_to_text(self, audio_path: str, source_lang: str = "auto") -> STTResult:
        """
        Transcribe audio with automatic language detection.
        
        Args:
            audio_path: Path to audio file
            source_lang: Language hint (not required, Deepgram auto-detects)
            
        Returns:
            STTResult with transcribed text, confidence, and detected language
        """
        self._throttle()
        
        # Build query parameters for Deepgram API
        # Optimized for speed while maintaining multi-language support
        params = {
            "model": "nova-2",  # Base doesn't support language=multi
            "language": "multi",  # Auto-detect language
            "detect_language": "true",  # Return detected language
            # Minimal parameters for speed
        }
        
        url = f"{self._base_url}/listen"
        
        try:
            with open(audio_path, "rb") as audio_file:
                headers = self._headers()
                
                resp = requests.post(
                    url,
                    headers=headers,
                    params=params,
                    data=audio_file,
                    timeout=DEFAULT_TIMEOUT
                )
                resp.raise_for_status()
                
        except requests.exceptions.HTTPError as e:
            print("\n[Deepgram API Error]")
            print(f"Status code: {resp.status_code}")
            try:
                print(f"Response: {resp.json()}")
            except Exception:
                print(f"Raw response: {resp.text}")
            raise
        except FileNotFoundError:
            raise RuntimeError(f"Audio file not found: {audio_path}")
        
        payload = resp.json()
        
        # DEBUG: Log the full response for troubleshooting
        print(f"\n[Deepgram Response Debug]")
        print(f"Full response: {payload}")
        
        # Extract results from Deepgram response
        try:
            results = payload.get("results", {})
            channels = results.get("channels", [{}])
            
            if not channels or len(channels) == 0:
                print(f"[Deepgram Error] No channels in response")
                print(f"Response structure: {payload}")
                raise RuntimeError("Deepgram returned no channels")
            
            alternatives = channels[0].get("alternatives", [{}])
            
            if not alternatives or len(alternatives) == 0:
                print(f"[Deepgram Error] No alternatives in response")
                print(f"Channels data: {channels}")
                raise RuntimeError("Deepgram returned empty alternatives")
            
            transcript = alternatives[0].get("transcript", "").strip()
            confidence = alternatives[0].get("confidence", 0.0)
            
            # Extract detected language
            detected_language = channels[0].get("detected_language")
            
            print(f"[Deepgram] Transcript: '{transcript}'")
            print(f"[Deepgram] Confidence: {confidence}")
            print(f"[Deepgram] Detected language: {detected_language}")
            
            # Handle empty transcript (silence or inaudible audio)
            if not transcript or len(transcript) == 0:
                print(f"[Deepgram Warning] Empty transcript returned - audio may be silent or inaudible")
                # Return a special marker that the pipeline can handle
                return STTResult(
                    text="[SILENCE_DETECTED]",
                    confidence=0.0,
                    language="auto"
                )
            
            # Map Deepgram language codes to our format
            # Deepgram returns ISO codes like "hi", "ta", "te", "en"
            lang_code = self._map_language_code(detected_language)
            
            print(f"[Deepgram] Mapped language code: {lang_code}")
            
            return STTResult(
                text=transcript,
                confidence=confidence,
                language=lang_code
            )
            
        except (KeyError, IndexError) as e:
            print(f"Error parsing Deepgram response: {e}")
            print(f"Response structure: {payload}")
            raise RuntimeError(f"Failed to parse Deepgram response: {e}")
    
    def _map_language_code(self, deepgram_lang: Optional[str]) -> str:
        """
        Map Deepgram language codes to our internal format.
        
        Args:
            deepgram_lang: Language code from Deepgram (e.g., "hi", "ta-IN", "en-US")
            
        Returns:
            Normalized language code (e.g., "hi", "ta", "en")
        """
        if not deepgram_lang:
            return "auto"
        
        # Extract base language code (e.g., "hi" from "hi-IN")
        base_lang = deepgram_lang.split("-")[0].lower()
        
        # Map to our supported languages
        lang_map = {
            "hi": "hi",  # Hindi
            "ta": "ta",  # Tamil
            "te": "te",  # Telugu
            "kn": "kn",  # Kannada
            "ml": "ml",  # Malayalam
            "mr": "mr",  # Marathi
            "pa": "pa",  # Punjabi
            "bn": "bn",  # Bengali
            "gu": "gu",  # Gujarati
            "or": "or",  # Odia
            "en": "en",  # English
        }
        
        return lang_map.get(base_lang, "auto")
