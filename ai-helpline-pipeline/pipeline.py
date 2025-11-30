import logging
from dataclasses import dataclass
from typing import Optional

# Handle both package and direct imports
try:
    from .config import AppConfig, SUPPORTED_LANGUAGES, validate_language_code
    from .api_clients.elevenlabs_client import ElevenLabsClient
    from .api_clients.sarvam_client import SarvamClient
    from .api_clients.groq_client import GroqClient
except ImportError:
    from config import AppConfig, SUPPORTED_LANGUAGES, validate_language_code
    from api_clients.elevenlabs_client import ElevenLabsClient
    from api_clients.sarvam_client import SarvamClient
    from api_clients.groq_client import GroqClient


@dataclass
class PipelineResult:
	input_language: str
	transcribed_text: str
	translated_query: Optional[str]
	llm_response_en: str
	final_text: str
	output_audio_bytes: bytes


class HelplinePipeline:
	def __init__(self, config: AppConfig, logger: Optional[logging.Logger] = None):
		self.config = config
		self.logger = logger or logging.getLogger(__name__)
		# Use the new ElevenLabsClient
		self.speech = ElevenLabsClient(config)
		self.sarvam = SarvamClient(config)
		self.grog = GroqClient(config)

	def process_audio(
		self,
		audio_path: str,
		source_lang: str = "auto",
		target_lang: str = "en",
	) -> PipelineResult:
		if not validate_language_code(source_lang):
			raise ValueError(f"Unsupported source language: {source_lang}")
		if not validate_language_code(target_lang) and target_lang != "en":
			raise ValueError(f"Unsupported target language: {target_lang}")

		self.logger.info("Step 1: Converting speech to text...")
		stt = self.speech.speech_to_text(audio_path, source_lang=source_lang)
		self.logger.info("Transcribed text: %s", stt.text)

		effective_source = stt.language or source_lang

		translated_query: Optional[str] = None
		query_for_llm = stt.text
		if effective_source == "auto":
			# Cannot translate if language is unknown; use transcribed text as-is
			translated_query = None
			query_for_llm = stt.text
			self.logger.warning("Source language is 'auto'; skipping translation to English.")
		else:
			src_code = f"{effective_source}-IN"
			tr = self.sarvam.translate(
				stt.text,
				source_lang=src_code,
				target_lang="en-IN"
			)
			translated_query = tr.translated_text
			query_for_llm = translated_query
			self.logger.info("Translated query: %s", translated_query)

		self.logger.info("Step 3: Processing query with LLM...")
		system_prompt = (
			"You are a helpful agricultural helpline assistant for Indian farmers. "
			"Provide practical, safe, and region-agnostic advice. Keep answers concise."
		)
		llm_response_en = self.grog.chat(system_prompt=system_prompt, user_prompt=query_for_llm)
		self.logger.info("LLM response: %s", llm_response_en)

		final_text = llm_response_en
		if effective_source not in ("en", "auto"):
			self.logger.info("Step 4: Translating response back to %s...", effective_source)
			# FIX: Format the language codes for the translation back as well
			back = self.sarvam.translate(
				llm_response_en,
				source_lang="en-IN",
				target_lang=f"{effective_source}-IN"
			)
			final_text = back.translated_text
			self.logger.info("Final translated response: %s", final_text)

		self.logger.info("Step 5: Converting text to speech...")
		audio_bytes = self.speech.text_to_speech(final_text, target_lang=effective_source)

		return PipelineResult(
			input_language=effective_source,
			transcribed_text=stt.text,
			translated_query=translated_query,
			llm_response_en=llm_response_en,
			final_text=final_text,
			output_audio_bytes=audio_bytes,
		)