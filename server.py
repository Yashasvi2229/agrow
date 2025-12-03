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
    This endpoint returns TwiML to record the caller's question.
    """
    logger.info("Incoming call received")
    
    response = VoiceResponse()
    
    # Greet the caller
    response.say(
        "Welcome to Agrow, the AI-powered agricultural helpline for farmers. "
        "Please ask your question in any Indian language after the beep.",
        voice="Polly.Aditi",  # Indian English voice
        language="en-IN"
    )
    
    # Record the caller's question
    # maxLength=30 means 30 seconds max recording
    # action= is where Twilio will POST the recording URL
    response.record(
        max_length=30,
        action="/voice/recording",
        method="POST",
        play_beep=True,
        timeout=3,  # Stop recording after 3 seconds of silence
        transcribe=False
    )
    
    logger.info("Sent TwiML to record caller's question")
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route("/voice/recording", methods=["POST"])
def handle_recording():
    """
    Handle the recorded audio from Twilio.
    Download the recording, process through pipeline, and return TwiML to play response.
    """
    logger.info("Recording received from Twilio")
    
    # Get recording URL from Twilio
    recording_url = request.form.get("RecordingUrl")
    call_sid = request.form.get("CallSid")
    
    if not recording_url:
        logger.error("No recording URL provided")
        response = VoiceResponse()
        response.say("Sorry, we couldn't receive your question. Please try again.")
        return str(response), 200, {'Content-Type': 'text/xml'}
    
    logger.info(f"Call SID: {call_sid}")
    logger.info(f"Recording URL: {recording_url}")
    
    response = VoiceResponse()
    
    # Check if pipeline is ready
    if pipeline is None:
        logger.error("Pipeline not initialized")
        response.say("Sorry, the service is currently unavailable. Please try again later.")
        return str(response), 200, {'Content-Type': 'text/xml'}
    
    try:
        # Download the recording immediately
        logger.info("Downloading recording from Twilio...")
        audio_data = download_twilio_recording(recording_url)
        
        # Save to temp file
        input_audio_path = TEMP_DIR / f"{call_sid}_input.wav"
        with open(input_audio_path, "wb") as f:
            f.write(audio_data)
        logger.info(f"Recording saved to {input_audio_path}")
        
        # Process through pipeline
        logger.info("Processing through AI pipeline...")
        result = pipeline.process_audio(
            audio_path=str(input_audio_path),
            source_lang="auto",  # Auto-detect language
            target_lang="en"
        )
        
        # Save output audio
        output_audio_path = OUTPUT_DIR / f"{call_sid}_response.wav"
        with open(output_audio_path, "wb") as f:
            f.write(result.output_audio_bytes)
        logger.info(f"Response saved to {output_audio_path}")
        
        # Generate public URL for the audio file
        # For local dev, you'll need ngrok or similar
        base_url = request.url_root.rstrip('/')
        audio_url = f"{base_url}/audio/{call_sid}_response.wav"
        
        logger.info(f"Playing response audio: {audio_url}")
        
        # Play the response audio
        response.play(audio_url)
        
        # Thank the caller
        response.say(
            "Thank you for using Agrow. Have a great day!",
            voice="Polly.Aditi",
            language="en-IN"
        )
        
        # Clean up temp file
        input_audio_path.unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"Error processing call: {e}", exc_info=True)
        response.say(
            "Sorry, we encountered an error processing your question. Please try again.",
            voice="Polly.Aditi",
            language="en-IN"
        )
    
    return str(response), 200, {'Content-Type': 'text/xml'}


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
        
        return audio_data, 200, {
            'Content-Type': 'audio/wav',
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
