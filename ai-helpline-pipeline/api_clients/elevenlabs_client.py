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


class ElevenLabsClient:
    def __init__(self, config: AppConfig):
        self._api_key = config.elevenlabs_api_key
        self._base_url = config.endpoints.elevenlabs_base_url.rstrip("/")
        self._rate_per_min = config.rate_limits.stt_per_minute  # You might want separate rate limits
        self._last_ts: float = 0.0
        # Store model/voice configs for easier access
        self._stt_model = getattr(config.models, "elevenlabs_stt_model", "scribe_v1")
        self._tts_model = getattr(config.models, "elevenlabs_tts_model", "eleven_multilingual_v2")
        self._default_voice_id = getattr(config.models, "elevenlabs_tts_voice_id", "iWNf11sz1GrUE4ppxTOL")  # Default to 'Rachel'

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
            "xi-api-key": self._api_key,
        }

    def speech_to_text(self, audio_path: str, source_lang: str = "auto") -> STTResult:
        self._throttle()
        url = f"{self._base_url}/speech-to-text"

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/.wav")}
            data = {"model_id": self._stt_model}
            headers = self._headers()
            try:
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("\n[ElevenLabs API Error]")
                print(f"Status code: {resp.status_code}")
                try:
                    print(f"Response: {resp.json()}")
                except Exception:
                    print(f"Raw response: {resp.text}")
                raise
            payload = resp.json()
            text = payload.get("text", "").strip()
            if not text:
                raise RuntimeError("STT returned empty text")
            return STTResult(text=text, confidence=1.0, language=source_lang)

    def text_to_speech(self, text: str, target_lang: str, voice: Optional[str] = None) -> bytes:
        self._throttle()
        voice_id = voice or self._default_voice_id
        url = f"{self._base_url}/text-to-speech/{voice_id}"
        json_payload = {
            "text": text,
            "model_id": self._tts_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        try:
            resp = requests.post(url, headers=headers, json=json_payload, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print("\n[ElevenLabs TTS API Error]")
            print(f"Status code: {resp.status_code}")
            try:
                print(f"Response: {resp.json()}")
            except Exception:
                print(f"Raw response: {resp.text}")
            print(f"Request payload: {json_payload}")
            print(f"Request URL: {url}")
            raise
        return resp.content