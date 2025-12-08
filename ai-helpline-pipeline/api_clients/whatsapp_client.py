"""
WhatsApp Client Module

Handles sending call summaries via Twilio WhatsApp API.
Translates summaries to caller's language using Sarvam AI.
"""

import os
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Import Sarvam client for translation
try:
    from .sarvam_client import SarvamClient
except ImportError:
    from sarvam_client import SarvamClient


logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Client for sending WhatsApp messages via Twilio"""
    
    def __init__(self):
        """Initialize Twilio WhatsApp client"""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
        
        if not all([self.account_sid, self.auth_token, whatsapp_from]):
            logger.error("Missing Twilio WhatsApp configuration")
            raise ValueError("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM must be set")
        
        # Ensure whatsapp_from has the correct prefix
        if not whatsapp_from.startswith("whatsapp:"):
            self.whatsapp_from = f"whatsapp:{whatsapp_from}"
            logger.info(f"Added whatsapp: prefix to FROM number: {self.whatsapp_from}")
        else:
            self.whatsapp_from = whatsapp_from
        
        self.client = Client(self.account_sid, self.auth_token)
        logger.info("WhatsApp client initialized successfully")
        
        # Initialize Sarvam client for translation
        # Import config to create Sarvam client properly
        try:
            from config import load_config
            config = load_config()
            self.sarvam_client = SarvamClient(config=config)
        except Exception as e:
            logger.warning(f"Failed to initialize Sarvam client: {e}")
            self.sarvam_client = None
    
    def send_whatsapp_message(self, to_number: str, message: str) -> bool:
        """
        Send a WhatsApp message to a phone number.
        
        Args:
            to_number: Phone number in format +91XXXXXXXXXX
            message: Message text to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Ensure phone number is in WhatsApp format
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            # Send message via Twilio
            message_obj = self.client.messages.create(
                from_=self.whatsapp_from,
                body=message,
                to=to_number
            )
            
            logger.info(f"WhatsApp message sent successfully. SID: {message_obj.sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending WhatsApp message: {e.msg} (Code: {e.code})")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
            return False
    
    def translate_summary(self, summary_text: str, target_lang: str) -> Optional[str]:
        """
        Translate English summary to target language using Sarvam AI.
        
        Args:
            summary_text: Summary text in English
            target_lang: Target language code (hi, ta, te, etc.)
            
        Returns:
            Translated text, or None if translation fails
        """
        # If target is English, no translation needed
        if target_lang == "en":
            return summary_text
        
        if not self.sarvam_client:
            logger.error("Sarvam client not initialized, cannot translate")
            return None
        
        try:
            # Sarvam expects language codes with -IN suffix
            sarvam_target_lang = f"{target_lang}-IN"
            
            logger.info(f"Translating summary to {sarvam_target_lang}")
            result = self.sarvam_client.translate(
                text=summary_text,
                source_lang="en-IN",
                target_lang=sarvam_target_lang  # Fixed: Add -IN suffix
            )
            logger.info(f"Translation successful to {target_lang}")
            return result.translated_text  # Extract text from TranslationResult object
        except Exception as e:
            logger.error(f"Translation failed: {e}", exc_info=True)
            return None
    
    def send_conversation_summary(
        self, 
        caller_number: str, 
        summary_en: str, 
        language: str
    ) -> bool:
        """
        Main function to translate and send conversation summary via WhatsApp.
        
        Args:
            caller_number: Caller's phone number
            summary_en: Conversation summary in English
            language: Caller's detected language
            
        Returns:
            True if summary sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending conversation summary to {caller_number} in {language}")
            
            # Translate summary to caller's language
            if language == "en":
                translated_summary = summary_en
            else:
                translated_summary = self.translate_summary(summary_en, language)
                
                # Fallback to English if translation fails
                if not translated_summary:
                    logger.warning(f"Translation failed, sending in English")
                    translated_summary = summary_en
            
            # Send via WhatsApp
            success = self.send_whatsapp_message(caller_number, translated_summary)
            
            if success:
                logger.info(f"Conversation summary sent successfully to {caller_number}")
            else:
                logger.error(f"Failed to send conversation summary to {caller_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in send_conversation_summary: {e}", exc_info=True)
            return False


def send_summary_via_whatsapp(
    caller_number: str, 
    summary: str, 
    language: str = "en"
) -> bool:
    """
    Convenience function to send summary via WhatsApp.
    
    Args:
        caller_number: Caller's phone number
        summary: Conversation summary (in English)
        language: Target language code
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        client = WhatsAppClient()
        return client.send_conversation_summary(caller_number, summary, language)
    except Exception as e:
        logger.error(f"Failed to send WhatsApp summary: {e}", exc_info=True)
        return False
