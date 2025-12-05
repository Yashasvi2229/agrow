import os
import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator
import requests
from dotenv import load_dotenv

# Add ai-helpline-pipeline to Python path
sys.path.insert(0, str(Path(__file__).parent / "ai-helpline-pipeline"))

# Import the existing pipeline
from pipeline import HelplinePipeline
from config import load_config

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize pipeline
try:
    config = load_config()
    pipeline = HelplinePipeline(config=config, logger=logger)
    logger.info("Pipeline initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pipeline: {e}")
    pipeline = None

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Create directories
TEMP_DIR = Path("temp_uploads")
OUTPUT_DIR = Path("output_audio")
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory storage for call language preferences
# In production, use Redis or database
call_language_map = {}

# India STD code → Language mapping for phone-based language detection
# Maps area codes to primary languages spoken in those regions
STD_TO_LANGUAGE = {
    # Hindi belt (North India)
    "11": "hi",    # Delhi
    "120": "hi",   # Noida
    "121": "hi",   # Faridabad
    "124": "hi",   # Gurgaon
    "141": "hi",   # Jaipur
    "145": "hi",   # Ajmer
    "161": "hi",   # Ludhiana
    "172": "pa",   # Chandigarh (Punjabi)
    "181": "pa",   # Jammu
    "191": "hi",   # UP - Meerut
    "522": "hi",   # Lucknow
    "512": "hi",   # Kanpur
    "542": "hi",   # Varanasi
    "562": "hi",   # Agra
    "571": "hi",   # Aligarh
    "612": "hi",   # Patna
    "651": "hi",   # Ranchi
    
    # Marathi (Maharashtra)
    "22": "mr",    # Mumbai
    "20": "mr",    # Pune
    "212": "mr",   # Aurangabad
    "231": "mr",   # Nagpur
    "251": "mr",   # Nashik
    
    # Tamil (Tamil Nadu)
    "44": "ta",    # Chennai
    "422": "ta",   # Coimbatore
    "427": "ta",   # Salem
    "452": "ta",   # Madurai
    "462": "ta",   # Tiruchirapalli
    
    # Telugu (Telangana & Andhra Pradesh) 
    "40": "te",    # Hyderabad
    "863": "te",   # Vijayawada
    "891": "te",   # Visakhapatnam
    "866": "te",   # Guntur
    
    # Kannada (Karnataka)
    "80": "kn",    # Bangalore
    "821": "kn",   # Mysore
    "824": "kn",   # Mangalore
    "836": "kn",   # Belgaum
    
    # Bengali (West Bengal)
    "33": "bn",    # Kolkata
    "341": "bn",   # Siliguri
    "353": "bn",   # Durgapur
    
    # Gujarati (Gujarat)
    "79": "gu",    # Ahmedabad
    "261": "gu",   # Surat
    "265": "gu",   # Vadodara
    "281": "gu",   # Rajkot
}

# Multi-language prompts for TwiML messages
LANGUAGE_PROMPTS = {
    "hi": {  # Hindi
        "welcome": "एग्रोवाइज़ में आपका स्वागत है। यह किसानों के लिए AI-संचालित कृषि हेल्पलाइन है। कृपया बीप के बाद अपना सवाल किसी भी भारतीय भाषा में पूछें।",
        "processing": "आपके प्रश्न की प्रक्रिया की जा रही है। कृपया प्रतीक्षा करें।",
        "still_processing": "अभी भी प्रक्रिया जारी है। कृपया धैर्य रखें।",
        "thank_you": "एग्रोवाइज़ का उपयोग करने के लिए धन्यवाद। अच्छा दिन हो!",
        "error": "क्षमा करें, आपके प्रश्न को संसाधित करने में त्रुटि हुई। कृपया पुनः प्रयास करें।"
    },
    "ta": {  # Tamil
        "welcome": "அக்ரோவைஸுக்கு வரவேற்கிறோம். இது விவசாயிகளுக்கான AI-இயக்கப்படும் வேளாண் உதவி எண். பீப் ஒலிக்குப் பிறகு உங்கள் கேள்வியை எந்த இந்திய மொழியிலும் கேட்கவும்.",
        "processing": "உங்கள் கேள்வி செயலாக்கப்படுகிறது. தயவுசெய்து காத்திருக்கவும்.",
        "still_processing": "இன்னும் செயலாக்கம் தொடர்கிறது. தயவுசெய்து பொறுமையாக இருங்கள்.",
        "thank_you": "அக்ரோவைஸைப் பயன்படுத்தியதற்கு நன்றி. நல்ல நாள்!",
        "error": "மன்னிக்கவும், உங்கள் கேள்வியை செயலாக்குவதில் பிழை ஏற்பட்டது. தயவுசெய்து மீண்டும் முயற்சிக்கவும்."
    },
    "te": {  # Telugu
        "welcome": "ఆగ్రోవైజ్‌కు స్వాగతం. ఇది రైతుల కోసం AI-ఆధారిత వ్యవసాయ హెల్ప్‌లైన్. బీప్ తర్వాత మీ ప్రశ్నను ఏ భారతీయ భాషలోనైనా అడగండి.",
        "processing": "మీ ప్రశ్న ప్రాసెస్ అవుతోంది. దయచేసి వేచి ఉండండి.",
        "still_processing": "ఇంకా ప్రాసెసింగ్ కొనసాగుతోంది. దయచేసి ఓపిక పట్టండి.",
        "thank_you": "ఆగ్రోవైజ్ ఉపయోగించినందుకు ధన్యవాదాలు. మంచి రోజు!",
        "error": "క్షమించండి, మీ ప్రశ్నను ప్రాసెస్ చేయడంలో లోపం ఉంది. దయచేసి మళ్లీ ప్రయత్నించండి."
    },
    "kn": {  # Kannada
        "welcome": "ಆಗ್ರೋವೈಸ್‌ಗೆ ಸ್ವಾಗತ. ಇದು ರೈತರಿಗಾಗಿ AI-ಚಾಲಿತ ಕೃಷಿ ಸಹಾಯವಾಣಿ. ಬೀಪ್ ನಂತರ ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಯಾವುದೇ ಭಾರತೀಯ ಭಾಷೆಯಲ್ಲಿ ಕೇಳಿ.",
        "processing": "ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ. ದಯವಿಟ್ಟು ನಿರೀಕ್ಷಿಸಿ.",
        "still_processing": "ಇನ್ನೂ ಪ್ರಕ್ರಿಯೆ ಮುಂದುವರಿಯುತ್ತಿದೆ. ದಯವಿಟ್ಟು ತಾಳ್ಮೆ ಇರಿಸಿ.",
        "thank_you": "ಆಗ್ರೋವೈಸ್ ಬಳಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು. ಶುಭ ದಿನ!",
        "error": "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುವಲ್ಲಿ ದೋಷವಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ."
    },
    "mr": {  # Marathi
        "welcome": "एग्रोवाईझमध्ये आपले स्वागत आहे. ही शेतकऱ्यांसाठी AI-चालित कृषी हेल्पलाइन आहे. बीप नंतर कृपया आपला प्रश्न कोणत्याही भारतीय भाषेत विचारा.",
        "processing": "आपल्या प्रश्नावर प्रक्रिया केली जात आहे. कृपया प्रतीक्षा करा.",
        "still_processing": "अजूनही प्रक्रिया सुरू आहे. कृपया धीर धरा.",
        "thank_you": "एग्रोवाईझ वापरल्याबद्दल धन्यवाद. चांगला दिवस असो!",
        "error": "माफ करा, आपला प्रश्न प्रक्रिया करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा."
    },
    "pa": {  # Punjabi
        "welcome": "ਐਗਰੋਵਾਈਜ਼ ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ। ਇਹ ਕਿਸਾਨਾਂ ਲਈ AI-ਸੰਚਾਲਿਤ ਖੇਤੀਬਾੜੀ ਹੈਲਪਲਾਈਨ ਹੈ। ਬੀਪ ਤੋਂ ਬਾਅਦ ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਕਿਸੇ ਵੀ ਭਾਰਤੀ ਭਾਸ਼ਾ ਵਿੱਚ ਪੁੱਛੋ।",
        "processing": "ਤੁਹਾਡੇ ਸਵਾਲ ਦੀ ਪ੍ਰਕ੍ਰਿਆ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਉਡੀਕ ਕਰੋ।",
        "still_processing": "ਅਜੇ ਵੀ ਪ੍ਰਕ੍ਰਿਆ ਜਾਰੀ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਸਬਰ ਕਰੋ।",
        "thank_you": "ਐਗਰੋਵਾਈਜ਼ ਵਰਤਣ ਲਈ ਧੰਨਵਾਦ। ਚੰਗਾ ਦਿਨ!",
        "error": "ਮਾਫ਼ ਕਰਨਾ, ਤੁਹਾਡੇ ਸਵਾਲ ਦੀ ਪ੍ਰਕ੍ਰਿਆ ਵਿੱਚ ਗਲਤੀ ਹੋਈ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।"
    },
    "bn": {  # Bengali
        "welcome": "অ্যাগ্রোওয়াইজ-এ আপনাকে স্বাগতম। এটি কৃষকদের জন্য AI-চালিত কৃষি হেল্পলাইন। বিপের পরে দয়া করে যেকোনো ভারতীয় ভাষায় আপনার প্রশ্ন জিজ্ঞাসা করুন।",
        "processing": "আপনার প্রশ্ন প্রক্রিয়াধীন। দয়া করে অপেক্ষা করুন।",
        "still_processing": "এখনও প্রক্রিয়া চলছে। দয়া করে ধৈর্য ধরুন।",
        "thank_you": "অ্যাগ্রোওয়াইজ ব্যবহার করার জন্য ধন্যবাদ। শুভ দিন!",
        "error": "দুঃখিত, আপনার প্রশ্ন প্রক্রিয়া করতে ত্রুটি হয়েছে। দয়া করে পুনরায় চেষ্টা করুন।"
    },
    "gu": {  # Gujarati
        "welcome": "એગ્રોવાઇઝમાં તમારું સ્વાગત છે. આ ખેડૂતો માટે AI-સંચાલિત કૃષિ હેલ્પલાઇન છે. બીપ પછી કૃપા કરીને કોઈપણ ભારતીય ભાષામાં તમારો પ્રશ્ન પૂછો.",
        "processing": "તમારા પ્રશ્નની પ્રક્રિયા થઈ રહી છે. કૃપા કરીને રાહ જુઓ.",
        "still_processing": "હજુ પણ પ્રક્રિયા ચાલુ છે. કૃપા કરીને ધીરજ રાખો.",
        "thank_you": "એગ્રોવાઇઝ વાપરવા બદલ આભાર. સારો દિવસ!",
        "error": "માફ કરશો, તમારા પ્રશ્નની પ્રક્રિયામાં ભૂલ આવી. કૃપા કરીને ફરી પ્રયાસ કરો."
    },
    "en": {  # English (fallback)
        "welcome": "Welcome to AgroWise, the AI-powered agricultural helpline for farmers. Please ask your question in any Indian language after the beep.",
        "processing": "Processing your question. Please wait.",
        "still_processing": "Still processing. Please continue to hold.",
        "thank_you": "Thank you for using AgroWise. Have a great day!",
        "error": "Sorry, we encountered an error processing your question. Please try again."
    }
}

def detect_language_from_phone(phone_number: str) -> str:
    """
    Detect language from Indian phone number based on STD code.
    
    Args:
        phone_number: Phone number in format +91XXXXXXXXXX
        
    Returns:
        Language code (hi, ta, te, etc.). Defaults to 'hi' if not found.
    """
    try:
        # Remove +91 country code
        if phone_number.startswith("+91"):
            phone_number = phone_number[3:]
        elif phone_number.startswith("91"):
            phone_number = phone_number[2:]
        
        # Try 3-digit STD code first
        std_code_3 = phone_number[:3]
        if std_code_3 in STD_TO_LANGUAGE:
            lang = STD_TO_LANGUAGE[std_code_3]
            logger.info(f"Detected language '{lang}' from STD code {std_code_3}")
            return lang
        
        # Try 2-digit STD code
        std_code_2 = phone_number[:2]
        if std_code_2 in STD_TO_LANGUAGE:
            lang = STD_TO_LANGUAGE[std_code_2]
            logger.info(f"Detected language '{lang}' from STD code {std_code_2}")
            return lang
        
        # Default to Hindi if no match
        logger.info(f"No STD code match for {phone_number[:4]}, defaulting to Hindi")
        return "hi"
        
    except Exception as e:
        logger.error(f"Error detecting language from phone: {e}")
        return "hi"  # Safe fallback


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "pipeline_ready": pipeline is not None
    }), 200


@app.route("/voice/incoming", methods=["POST"])
def incoming_call():
    """
    Handle incoming Twilio voice calls.
    Detect caller's language from phone number and greet in their language.
    """
    logger.info("Incoming call received")
    
    # Get caller's phone number and Call SID
    caller_number = request.form.get('From', '')
    call_sid = request.form.get('CallSid', '')
    logger.info(f"Call from: {caller_number}, CallSid: {call_sid}")
    
    # Detect language from phone number
    detected_lang = detect_language_from_phone(caller_number)
    
    # Store language preference for this call
    call_language_map[call_sid] = detected_lang
    
    # Get prompts for detected language
    prompts = LANGUAGE_PROMPTS.get(detected_lang, LANGUAGE_PROMPTS["en"])
    
    response = VoiceResponse()
    
    # Twilio language codes for Polly voices
    twilio_lang_map = {
        "hi": "hi-IN",
        "ta": "ta-IN",
        "te": "te-IN",
        "kn": "kn-IN",
        "mr": "mr-IN",
        "pa": "pa-IN",
        "bn": "bn-IN",
        "gu": "gu-IN",
        "en": "en-IN"
    }
    
    twilio_lang = twilio_lang_map.get(detected_lang, "hi-IN")
    
    # Greet the caller in their language
    response.say(
        prompts["welcome"],
        voice="Polly.Aditi",  # Indian voice - supports multiple Indic languages
        language=twilio_lang
    )
    
    # Record the caller's question
    response.record(
        max_length=30,
        action="/voice/recording",
        method="POST",
        play_beep=True,
        timeout=3,
        transcribe=False
    )
    
    logger.info(f"Sent TwiML in language '{detected_lang}' to record caller's question")
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route("/voice/recording", methods=["POST"])
def handle_recording():
    """
    Handle the recorded audio from Twilio.
    Immediately return TwiML with hold message, then process in background.
    """
    logger.info("Recording received from Twilio")
    
    # Get recording URL from Twilio
    recording_url = request.form.get("RecordingUrl")
    call_sid = request.form.get("CallSid")
    
    # Get stored language for this call (default to Hindi)
    detected_lang = call_language_map.get(call_sid, "hi")
    prompts = LANGUAGE_PROMPTS.get(detected_lang, LANGUAGE_PROMPTS["hi"])
    
    twilio_lang_map = {
        "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN",
        "mr": "mr-IN", "pa": "pa-IN", "bn": "bn-IN", "gu": "gu-IN", "en": "en-IN"
    }
    twilio_lang = twilio_lang_map.get(detected_lang, "hi-IN")
    
    if not recording_url:
        logger.error("No recording URL provided")
        response = VoiceResponse()
        response.say(prompts["error"], voice="Polly.Aditi", language=twilio_lang)
        return str(response), 200, {'Content-Type': 'text/xml'}
    
    logger.info(f"Call SID: {call_sid}")
    logger.info(f"Recording URL: {recording_url}")
    
    response = VoiceResponse()
    
    # Check if pipeline is ready
    if pipeline is None:
        logger.error("Pipeline not initialized")
        response.say(prompts["error"], voice="Polly.Aditi", language=twilio_lang)
        return str(response), 200, {'Content-Type': 'text/xml'}
    
    # IMMEDIATELY start processing in background (don't wait)
    import threading
    processing_thread = threading.Thread(
        target=process_audio_background,
        args=(recording_url, call_sid)
    )
    processing_thread.daemon = True
    processing_thread.start()
    
    # Return TwiML immediately with hold message in caller's language
    response.say(
        prompts["processing"],
        voice="Polly.Aditi",
        language=twilio_lang
    )
    
    # Use pause instead of music for faster polling
    # Pause for 5 seconds, then check if response is ready
    response.pause(length=5)
    
    # Redirect to check if processing is done (will check every 5 seconds)
    # Use absolute URL for Twilio redirect to work properly
    base_url = request.url_root.rstrip('/')
    response.redirect(f"{base_url}/voice/get-response/{call_sid}", method="GET")
    
    return str(response), 200, {'Content-Type': 'text/xml'}


def process_audio_background(recording_url: str, call_sid: str):
    """Process audio in background thread"""
    try:
        logger.info("Background processing started for " + call_sid)
        
        # Get phone-detected language for this call (if available)
        phone_detected_lang = call_language_map.get(call_sid, "hi")
        logger.info(f"Phone-detected language for {call_sid}: {phone_detected_lang}")
        
        # Download the recording
        logger.info("Downloading recording from Twilio...")
        audio_data = download_twilio_recording(recording_url)
        
        # Save to temp file
        input_audio_path = TEMP_DIR / f"{call_sid}_input.wav"
        with open(input_audio_path, "wb") as f:
            f.write(audio_data)
        logger.info(f"Recording saved to {input_audio_path}")
        
        # Process through pipeline with phone language hint
        logger.info("Processing through AI pipeline...")
        result = pipeline.process_audio(
            audio_path=str(input_audio_path),
            source_lang="auto",
            target_lang="en",
            phone_detected_lang=phone_detected_lang  # Pass language hint from phone
        )
        
        # Save output audio
        output_audio_path = OUTPUT_DIR / f"{call_sid}_response.wav"
        with open(output_audio_path, "wb") as f:
            f.write(result.output_audio_bytes)
        logger.info(f"Response saved to {output_audio_path}")
        
        # Clean up temp file
        input_audio_path.unlink(missing_ok=True)
        
        logger.info(f"Background processing complete for {call_sid}")
        
    except Exception as e:
        logger.error(f"Error in background processing: {e}", exc_info=True)


@app.route("/voice/get-response/<call_sid>", methods=["GET", "POST"])
def get_response(call_sid):
    """Check if response is ready and play it"""
    response = VoiceResponse()
    
    # Get stored language for this call (default to Hindi)
    detected_lang = call_language_map.get(call_sid, "hi")
    prompts = LANGUAGE_PROMPTS.get(detected_lang, LANGUAGE_PROMPTS["hi"])
    
    twilio_lang_map = {
        "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN",
        "mr": "mr-IN", "pa": "pa-IN", "bn": "bn-IN", "gu": "gu-IN", "en": "en-IN"
    }
    twilio_lang = twilio_lang_map.get(detected_lang, "hi-IN")
    
    # Check if response audio exists
    output_audio_path = OUTPUT_DIR / f"{call_sid}_response.wav"
    
    if output_audio_path.exists():
        # Response is ready! Play it
        base_url = request.url_root.rstrip('/')
        audio_url = f"{base_url}/audio/{call_sid}_response.wav"
        
        logger.info(f"Playing response audio: {audio_url}")
        response.play(audio_url)
        
        # Thank you message in caller's language
        response.say(
            prompts["thank_you"],
            voice="Polly.Aditi",
            language=twilio_lang
        )
        
        # Clean up language mapping for this call
        call_language_map.pop(call_sid, None)
    else:
        # Still processing, pause and check again
        logger.info(f"Response not ready yet for {call_sid}, continuing to wait")
        
        # Status message in caller's language
        response.say(
            prompts["still_processing"],
            voice="Polly.Aditi",
            language=twilio_lang
        )
        # Pause for 5 seconds then check again
        response.pause(length=5)
        # Use absolute URL for redirect
        base_url = request.url_root.rstrip('/')
        response.redirect(f"{base_url}/voice/get-response/{call_sid}", method="GET")
    
    twiml_str = str(response)
    logger.info(f"Returning TwiML: {twiml_str[:200]}...")  # Log first 200 chars
    return twiml_str, 200, {'Content-Type': 'text/xml'}


@app.route("/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    """Serve audio files for Twilio to play"""
    try:
        audio_path = OUTPUT_DIR / filename
        if not audio_path.exists():
            logger.error(f"Audio file not found: {filename}")
            return "File not found", 404
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # ElevenLabs returns MP3 format despite .wav extension
        # Set correct Content-Type for Twilio
        return audio_data, 200, {
            'Content-Type': 'audio/mpeg',
            'Content-Disposition': f'inline; filename="{filename}"'
        }
    except Exception as e:
        logger.error(f"Error serving audio: {e}")
        return "Error serving file", 500


def download_twilio_recording(recording_url: str) -> bytes:
    """Download audio recording from Twilio"""
    # Twilio recordings require authentication
    # Add .wav to get WAV format instead of MP3
    wav_url = f"{recording_url}.wav"
    
    response = requests.get(
        wav_url,
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        timeout=30
    )
    response.raise_for_status()
    
    return response.content


if __name__ == "__main__":
    # Check required environment variables
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
        logger.error("Missing Twilio credentials. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        exit(1)
    
    logger.info("Starting Agrow Twilio Server...")
    logger.info(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER or 'Not set'}")
    
    # Run Flask app
    # For production, use a proper WSGI server like gunicorn
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )
