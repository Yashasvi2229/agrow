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
	# Supported Indian languages for validation
	INDIAN_LANGUAGES = {"hi", "ta", "te", "kn", "mr", "pa", "bn", "gu", "ml", "or", "en"}
	
	def __init__(self, config: AppConfig, logger: Optional[logging.Logger] = None):
		self.config = config
		self.logger = logger or logging.getLogger(__name__)
		# Use the new ElevenLabsClient
		self.speech = ElevenLabsClient(config)
		self.sarvam = SarvamClient(config)
		self.grog = GroqClient(config)

	def _detect_language_from_script(self, text: str) -> Optional[str]:
		"""
		Detect language from Unicode script/characters in the text.
		Returns language code if detected, None otherwise.
		"""
		if not text:
			return None
			
		# Unicode ranges for Indian language scripts
		script_ranges = {
			"hi": (0x0900, 0x097F),  # Devanagari (Hindi, Marathi)
			"ta": (0x0B80, 0x0BFF),  # Tamil
			"te": (0x0C00, 0x0C7F),  # Telugu
			"kn": (0x0C80, 0x0CFF),  # Kannada
			"ml": (0x0D00, 0x0D7F),  # Malayalam
			"bn": (0x0980, 0x09FF),  # Bengali
			"gu": (0x0A80, 0x0AFF),  # Gujarati
			"pa": (0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
			"or": (0x0B00, 0x0B7F),  # Oriya
		}
		
		# Count characters in each script
		script_counts = {lang: 0 for lang in script_ranges}
		
		for char in text:
			code_point = ord(char)
			for lang, (start, end) in script_ranges.items():
				if start <= code_point <= end:
					script_counts[lang] += 1
					break
		
		# Return language with most characters (if > 5 chars detected)
		max_lang = max(script_counts, key=script_counts.get)
		if script_counts[max_lang] > 5:
			self.logger.info(f"Detected script: {max_lang} ({script_counts[max_lang]} characters)")
			return max_lang
		
		return None

	def process_audio(
		self,
		audio_path: str,
		source_lang: str = "auto",
		target_lang: str = "en",
		phone_detected_lang: Optional[str] = None,  # NEW: Language hint from phone number
	) -> PipelineResult:
		if not validate_language_code(source_lang):
			raise ValueError(f"Unsupported source language: {source_lang}")
		if not validate_language_code(target_lang) and target_lang != "en":
			raise ValueError(f"Unsupported target_lang: {target_lang}")

		self.logger.info("Step 1: Converting speech to text...")
		stt = self.speech.speech_to_text(audio_path, source_lang=source_lang)
		self.logger.info("Transcribed text: %s", stt.text)

		# Step 2: Validate and determine effective language
		detected_lang = stt.language or source_lang
		
		# Validate detected language
		if detected_lang != "auto" and detected_lang not in self.INDIAN_LANGUAGES:
			self.logger.warning(
				f"Suspicious language detected: '{detected_lang}' (not in expected Indian languages). "
				f"Using phone hint: {phone_detected_lang} as fallback."
			)
			detected_lang = phone_detected_lang or "hi"  # Use phone hint or default to Hindi
		
		# If still auto, try script detection first, then phone hint
		if detected_lang == "auto":
			# Try to detect from script/characters
			script_lang = self._detect_language_from_script(stt.text)
			if script_lang:
				self.logger.info(f"Using script-detected language: {script_lang}")
				detected_lang = script_lang
			elif phone_detected_lang:
				self.logger.info(f"Using phone-detected language: {phone_detected_lang}")
				detected_lang = phone_detected_lang
		
		# Final fallback to Hindi if still auto
		if detected_lang == "auto":
			self.logger.warning("Language still 'auto' after validation. Defaulting to Hindi.")
			detected_lang = "hi"
		
		effective_source = detected_lang
		self.logger.info(f"Effective language determined: {effective_source}")

		# Step 2: Translate to English if needed
		translated_query: Optional[str] = None
		query_for_llm = stt.text
		
		if effective_source != "en":
			# ALWAYS translate non-English to English for better LLM quality
			self.logger.info(f"Step 2: Translating from {effective_source} to English...")
			src_code = f"{effective_source}-IN"
			tr = self.sarvam.translate(
				stt.text,
				source_lang=src_code,
				target_lang="en-IN"
			)
			translated_query = tr.translated_text
			query_for_llm = translated_query
			self.logger.info("Translated query: %s", translated_query)
		else:
			self.logger.info("Input already in English, skipping translation")

		self.logger.info("Step 3: Processing query with LLM...")
		system_prompt = (
			"You are a helpful agricultural helpline assistant for Indian farmers. "
			"Provide practical, safe, and region-agnostic advice. Keep answers concise."
		)
		llm_response_en = self.grog.chat(system_prompt=system_prompt, user_prompt=query_for_llm)
		self.logger.info("LLM response: %s", llm_response_en)

		final_text = llm_response_en
		if effective_source != "en":
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