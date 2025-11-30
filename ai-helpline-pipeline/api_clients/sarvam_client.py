import time
from dataclasses import dataclass
from typing import Optional

import requests

try:
    from ..config import AppConfig
except ImportError:
    from config import AppConfig


DEFAULT_TIMEOUT = 30


@dataclass
class TranslationResult:
    translated_text: str
    quality_score: float
    source_lang: str
    target_lang: str


class SarvamClient:
    def __init__(self, config: AppConfig):
        # FIX: The API key for Sarvam is expected in a different header
        self._api_key = config.sarvam_api_key
        # FIX: Corrected the base URL to remove the /v1 part
        self._base_url = "https://api.sarvam.ai" 
        self._min_quality = config.quality.min_translation_quality
        self._rate_per_min = config.rate_limits.translation_per_minute
        self._last_ts: float = 0.0

    def _throttle(self) -> None:
        if self._rate_per_min <= 0:
            return
        interval = 60.0 / float(self._rate_per_min)
        delta = time.time() - self._last_ts
        if delta < interval:
            time.sleep(interval - delta)
        self._last_ts = time.time()

    def _headers(self) -> dict:
        # FIX: Sarvam expects the API key in the 'api-subscription-key' header
        return {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }

    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        self._throttle()
        # FIX: The correct endpoint is just /translate
        url = f"{self._base_url}/translate"
        
        # FIX: Updated the payload keys to match the Sarvam API
        payload = {
            "input": text,
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "model": "sarvam-translate:v1"  # Specifying the recommended model
        }
        
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print("\n[Sarvam API Error]")
            print(f"Status code: {resp.status_code}")
            try:
                print(f"Response: {resp.json()}")
            except Exception:
                print(f"Raw response: {resp.text}")
            raise
            
        data = resp.json()
        translated_text = data.get("translated_text", "").strip()
        
        # Sarvam's translate API doesn't return a quality score, so we'll default to 1.0
        quality_score = 1.0
        
        if not translated_text:
            raise RuntimeError("Translation returned empty text")
            
        return TranslationResult(
            translated_text=translated_text,
            quality_score=quality_score,
            source_lang=source_lang,
            target_lang=target_lang,
        )
