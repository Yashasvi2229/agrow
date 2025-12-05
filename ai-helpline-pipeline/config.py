import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
load_dotenv()


@dataclass(frozen=True)
class ServiceEndpoints:
	elevenlabs_base_url: str = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1")
	sarvam_base_url: str = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai/v1")
	groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
	google_tts_base_url: str = os.getenv("GOOGLE_TTS_BASE_URL", "https://texttospeech.googleapis.com/v1")


@dataclass(frozen=True)
class QualityConfig:
	min_stt_confidence: float = float(os.getenv("MIN_STT_CONFIDENCE", "0.7"))
	min_translation_quality: float = float(os.getenv("MIN_TRANSLATION_QUALITY", "0.6"))
	max_text_length: int = int(os.getenv("MAX_TEXT_LENGTH", "2000"))


@dataclass(frozen=True)
class RateLimits:
	stt_per_minute: int = int(os.getenv("RATE_LIMIT_STT", "10"))
	translation_per_minute: int = int(os.getenv("RATE_LIMIT_TRANSLATION", "60"))
	llm_per_minute: int = int(os.getenv("RATE_LIMIT_LLM", "20"))
	tts_per_minute: int = int(os.getenv("RATE_LIMIT_TTS", "10"))


@dataclass(frozen=True)
class ModelConfig:
	groq_model_name: str = os.getenv("GROQ_MODEL_NAME", "mixtral-8x7b-32768")


@dataclass(frozen=True)
class AppConfig:
	# Required
	elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
	sarvam_api_key: Optional[str] = os.getenv("SARVAM_API_KEY")
	groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
	google_tts_api_key: Optional[str] = os.getenv("GOOGLE_TTS_API_KEY")

	# Optional
	log_level: str = os.getenv("LOG_LEVEL", "INFO")
	debug_mode: bool = os.getenv("DEBUG_MODE", "false").lower() in {"1", "true", "yes", "on"}

	# Sub-configs
	endpoints: ServiceEndpoints = ServiceEndpoints()
	quality: QualityConfig = QualityConfig()
	rate_limits: RateLimits = RateLimits()
	models: ModelConfig = ModelConfig()

	# Language defaults
	default_source_lang: str = os.getenv("DEFAULT_SOURCE_LANG", "auto")
	default_target_lang: str = os.getenv("DEFAULT_TARGET_LANG", "en")


SUPPORTED_LANGUAGES = {
	"hi": "Hindi",
	"en": "English",
	"ta": "Tamil",
	"te": "Telugu",
	"bn": "Bengali",
	"gu": "Gujarati",
	"mr": "Marathi",
	"pa": "Punjabi",
	"kn": "Kannada",
	"ml": "Malayalam",
	"or": "Odia",
	"as": "Assamese",
	"ur": "Urdu",
	"ne": "Nepali",
}


def load_config() -> AppConfig:
	"""Load configuration from environment and validate required fields."""
	config = AppConfig()
	missing = []
	if not config.elevenlabs_api_key:
		missing.append("ELEVENLABS_API_KEY")
	if not config.sarvam_api_key:
		missing.append("SARVAM_API_KEY")
	if not config.groq_api_key:
		missing.append("GROQ_API_KEY")
	if not config.google_tts_api_key:
		missing.append("GOOGLE_TTS_API_KEY")
	if missing:
		raised = ", ".join(missing)
		raise RuntimeError(f"Missing required environment variables: {raised}. Create a .env and set keys.")
	return config


def validate_language_code(lang: str) -> bool:
	if lang == "auto":
		return True
	return lang in SUPPORTED_LANGUAGES


if __name__ == "__main__":
	try:
		cfg = load_config()
		print("Configuration loaded successfully.")
		print(f"Log level: {cfg.log_level}")
		print(f"Endpoints: {cfg.endpoints}")
		print(f"Quality: {cfg.quality}")
		print(f"RateLimits: {cfg.rate_limits}")
		print(f"Models: {cfg.models}")
	except Exception as exc:
		print(f"Configuration error: {exc}")
		raise
