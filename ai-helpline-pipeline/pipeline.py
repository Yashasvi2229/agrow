import logging
import re
from dataclasses import dataclass
from typing import Optional

# Handle both package and direct imports
try:
    from .config import AppConfig, SUPPORTED_LANGUAGES, validate_language_code
    from .api_clients.elevenlabs_client import ElevenLabsClient
    from .api_clients.sarvam_client import SarvamClient
    from .api_clients.groq_client import GroqClient
    from .api_clients.google_tts_client import GoogleTTSClient
except ImportError:
    from config import AppConfig, SUPPORTED_LANGUAGES, validate_language_code
    from api_clients.elevenlabs_client import ElevenLabsClient
    from api_clients.sarvam_client import SarvamClient
    from api_clients.groq_client import GroqClient
    from api_clients.google_tts_client import GoogleTTSClient


@dataclass
class PipelineResult:
	input_language: str
	transcribed_text: str
	translated_query: Optional[str]
	llm_response_en: str
	final_text: str
	output_audio_bytes: bytes
	is_valid_transcription: bool = True  # NEW: Flag for transcription quality


class HelplinePipeline:
	# Supported Indian languages for validation
	INDIAN_LANGUAGES = {"hi", "ta", "te", "kn", "mr", "pa", "bn", "gu", "ml", "or", "en"}
	
	def __init__(self, config: AppConfig, logger: Optional[logging.Logger] = None):
		self.config = config
		self.logger = logger or logging.getLogger(__name__)
		# Use ElevenLabs for STT (fast and accurate)
		self.speech_stt = ElevenLabsClient(config)
		# Use Google TTS for text-to-speech (faster than ElevenLabs)
		self.speech_tts = GoogleTTSClient(config)
		self.sarvam = SarvamClient(config)
		self.grog = GroqClient(config)

	def _is_valid_transcription(self, text: str) -> bool:
		"""
		Validate transcription quality to detect gibberish.
		
		TEMPORARILY DISABLED - Always returns True to allow continuous conversation
		despite ElevenLabs STT quality issues.
		
		Returns:
			True (validation disabled)
		"""
		# Validation disabled for hackathon - STT quality issues
		return True
		
		# Original validation code (commented out):
		# if not text or len(text.strip()) == 0:
		# 	return False
		# 
		# text_stripped = text.strip()
		# 
		# # Check 1: Too short (less than 2 characters total)
		# if len(text_stripped) < 2:
		# 	self.logger.warning(f"Transcription too short: '{text}'")
		# 	return False
		# 
		# # Check 2: Specific ElevenLabs error patterns
		# elevenlabs_errors = [
		# 	'(white noise)',
		# 	'(silence)',
		# 	'(blank)',
		# 	'(inaudible)',
		# 	'(unintelligible)',
		# 	'(background noise)',
		# 	'śmiech',
		# 	'(śmiech)',
		# 	'baronius',
		# 	'stargate',
		# ]
		# 
		# text_lower = text_stripped.lower()
		# for error in elevenlabs_errors:
		# 	if error in text_lower:
		# 		self.logger.warning(f"Detected ElevenLabs error pattern: '{text}'")
		# 		return False
		# 
		# self.logger.info(f"Transcription validation passed: '{text[:50]}...'")
		# return True

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
		conversation_history: Optional[list] = None,  # NEW: Previous Q&A for context
		pre_transcribed_text: Optional[str] = None,  # NEW: Use Twilio's transcription instead of ElevenLabs
	) -> PipelineResult:
		if not validate_language_code(source_lang):
			raise ValueError(f"Unsupported source language: {source_lang}")
		if not validate_language_code(target_lang) and target_lang != "en":
			raise ValueError(f"Unsupported target_lang: {target_lang}")

		# Step 1: Get transcription (use Twilio's if available, otherwise ElevenLabs)
		if pre_transcribed_text:
			self.logger.info(f"Using pre-transcribed text from Twilio: {pre_transcribed_text}")
			# Create a simple object with text and language attributes
			class STTResult:
				def __init__(self, text, language):
					self.text = text
					self.language = language
			stt = STTResult(text=pre_transcribed_text, language=phone_detected_lang or "auto")
		else:
			self.logger.info("Step 1: Converting speech to text via ElevenLabs...")
			stt = self.speech_stt.speech_to_text(audio_path, source_lang=source_lang)
		
		self.logger.info("Transcribed text: %s", stt.text)

		# Validate transcription quality
		if not self._is_valid_transcription(stt.text):
			self.logger.error(f"Invalid/gibberish transcription detected: '{stt.text}' - Asking user to repeat")
			# Use phone hint for retry message language, or default to Hindi
			retry_lang = phone_detected_lang or "hi"
			
			# Retry messages in different languages
			retry_messages = {
				"hi": "क्षमा करें, मुझे आपकी आवाज़ साफ नहीं सुनाई दी। कृपया अपना सवाल दोहराएं।",
				"ta": "மன்னிக்கவும், உங்கள் குரல் தெளிவாகக் கேட்கவில்லை. தயவுசெய்து உங்கள் கேள்வியை மீண்டும் கேளுங்கள்.",
				"te": "క్షమించండి, మీ స్వరం స్పష్టంగా వినిపించలేదు. దయచేసి మీ ప్రశ్నను మళ್లీ అడగండి.",
				"kn": "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಪುನರಾವರ್ತಿಸಿ.",
				"mr": "क्षमस्व, तुमचा आवाज स्पष्ट ऐकू आला नाही. कृपया तुमचा प्रश्न पुन्हा विचारा.",
				"pa": "ਮਾਫ਼ ਕਰਨਾ, ਤੁਹਾਡੀ ਆਵਾਜ਼ ਸਪੱਸ਼ਟ ਨਹੀਂ ਸੁਣਾਈ ਦਿੱਤੀ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਦੁਬਾਰਾ ਪੁੱਛੋ।",
				"bn": "দুঃখিত, আপনার কণ্ঠস্বর স্পষ্ট শুনিনি। অনুগ্রহ করে আবার জিজ্ঞাসা করুন।",
				"gu": "માફ કરશો, તમારો અવાજ સ્પષ્ટ સંભળાયો નહીં. કૃપા કરીને તમારો પ્રશ્ન ફરીથી પૂછો.",
				"en": "Sorry, I couldn't hear you clearly. Please repeat your question."
			}
			
			retry_message = retry_messages.get(retry_lang, retry_messages["hi"])
			
			# Generate audio for retry message
			retry_audio = self.speech_tts.text_to_speech(retry_message, target_lang=retry_lang)
			
			return PipelineResult(
				input_language=retry_lang,
				transcribed_text=stt.text,
				translated_query=None,
				llm_response_en="[RETRY_NEEDED]",
				final_text=retry_message,
				output_audio_bytes=retry_audio,
				is_valid_transcription=False  # Flag for invalid transcription
			)

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
		
		# Build conversation history context
		history_context = ""
		if conversation_history and len(conversation_history) > 0:
			history_context = "\n\nPrevious conversation:\n"
			for i, turn in enumerate(conversation_history, 1):
				history_context += f"Farmer Q{i}: {turn['question']}\n"
				history_context += f"Your A{i}: {turn['answer']}\n"
			history_context += "\nThe farmer's current question follows. Answer it considering the conversation history above."
		
		system_prompt = (
			"You are a helpful agricultural helpline assistant for Indian farmers. "
			"Provide practical, safe, and region-agnostic advice. "
			"Keep answers very concise - maximum 2 short sentences. "
			"Speak naturally for a phone call. Do not use any special formatting like asterisks, "
			"underscores, bullet points, or markdown symbols. Be direct and conversational. "
			"IMPORTANT: You MUST respond ONLY in English, regardless of the language in the conversation history. "
			"Your response will be translated to the farmer's language automatically."
			f"{history_context}"
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

		self.logger.info("Step 5: Converting text to speech with Google TTS...")
		audio_bytes = self.speech_tts.text_to_speech(final_text, target_lang=effective_source)

		return PipelineResult(
			input_language=effective_source,
			transcribed_text=stt.text,
			translated_query=translated_query,
			llm_response_en=llm_response_en,
			final_text=final_text,
			output_audio_bytes=audio_bytes,
		)