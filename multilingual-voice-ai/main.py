from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import httpx
import asyncio
import logging
from pathlib import Path
import uuid
from datetime import datetime

# Import our utility modules
from utils.whisper_handler import transcribe_audio
from utils.nlp_handler import extract_intent_and_entities
from utils.tts_handler import generate_speech
from utils.business_logic import get_bus_info_response

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Voice Bus System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
os.makedirs("twilio_audio", exist_ok=True)
os.makedirs("static/audio", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    """Home endpoint with API info"""
    return {
        "message": "🎯 AI Voice Bus System Ready!",
        "endpoints": {
            "voice": "/voice - Twilio webhook for incoming calls",
            "process_audio": "/process_audio - Process recorded audio",
            "test": "/test - Test endpoint"
        },
        "status": "🟢 Online"
    }

@app.post("/voice")
async def voice_webhook(request: Request):
    """
    Twilio voice webhook - Greets user and starts recording
    """
    logger.info("📞 Incoming call received!")
    
    # Get caller info
    form_data = await request.form()
    caller_number = form_data.get("From", "Unknown")
    
    logger.info(f"📞 Call from: {caller_number}")
    
    # Generate TwiML response
    twiml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="Polly.Aditi" language="hi-IN">
            Namaste! City Smart Bus Info mein aapka swagat hai. 
            Kaise madad kar sakte hain? Apna sawal puchiye.
        </Say>
        <Record 
            maxLength="30" 
            action="{str(request.base_url).rstrip('/')}/process_audio" 
            method="POST" 
            playBeep="true" 
            timeout="3"
            finishOnKey="#"
        />
        <Say voice="Polly.Aditi" language="hi-IN">
            Maaf kijiye, kuch samay ke liye hum upalabdh nahin hain. Dhanyawaad!
        </Say>
    </Response>'''
    
    return Response(content=twiml_response, media_type="application/xml")

@app.post("/process_audio")
async def process_audio_webhook(
    RecordingUrl: str = Form(...),
    RecordingSid: str = Form(...),
    CallSid: str = Form(...),
    From: str = Form(...)
):
    """
    Process the recorded audio from Twilio
    """
    try:
        logger.info(f"🎤 Processing audio: {RecordingSid}")
        
        # Step 1: Download the audio file
        audio_path = await download_twilio_recording(RecordingUrl, RecordingSid)
        logger.info(f"📁 Audio downloaded: {audio_path}")
        
        # Step 2: Speech-to-Text (Whisper)
        transcript, detected_language = await transcribe_audio(audio_path)
        logger.info(f"📝 Transcript: {transcript} (Language: {detected_language})")
        
        # Step 3: NLP Intent Recognition
        intent, entities = await extract_intent_and_entities(transcript, detected_language)
        logger.info(f"🧠 Intent: {intent}, Entities: {entities}")
        
        # Step 4: Business Logic
        response_text, language = await get_bus_info_response(intent, entities, detected_language)
        logger.info(f"📋 Response: {response_text}")
        
        # Step 5: Text-to-Speech
        audio_file_url = await generate_speech(response_text, language, str(request.base_url))
        logger.info(f"🔊 Audio generated: {audio_file_url}")
        
        # Step 6: Return TwiML with the audio response
        twiml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Play>{audio_file_url}</Play>
            <Pause length="1"/>
            <Say voice="Polly.Aditi" language="hi-IN">
                Aur kuch puchna chahte hain? Hash key dabayiye.
            </Say>
            <Pause length="3"/>
            <Say voice="Polly.Aditi" language="hi-IN">
                Aapka din shubh ho! Phir milenge!
            </Say>
            <Hangup/>
        </Response>'''
        
        # Cleanup the downloaded audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ Error processing audio: {e}")
        
        # Error response TwiML
        error_twiml = '''<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="Polly.Aditi" language="hi-IN">
                Maaf kijiye, kuch samay ke liye pareshani ho rahi hai. 
                Kripya dobara koshish kariye. Dhanyawaad!
            </Say>
            <Hangup/>
        </Response>'''
        
        return Response(content=error_twiml, media_type="application/xml")

async def download_twilio_recording(recording_url: str, recording_sid: str) -> str:
    """
    Download Twilio recording and save locally
    """
    try:
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}_{recording_sid}.wav"
        file_path = os.path.join("twilio_audio", filename)
        
        # Download the recording with authentication
        auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        
        async with httpx.AsyncClient() as client:
            # Add .wav to get WAV format
            wav_url = recording_url + ".wav"
            response = await client.get(wav_url, auth=auth)
            response.raise_for_status()
            
            # Save the file
            with open(file_path, "wb") as f:
                f.write(response.content)
        
        return file_path
        
    except Exception as e:
        logger.error(f"Error downloading recording: {e}")
        raise

@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    return {
        "status": "✅ Server is running",
        "timestamp": datetime.now().isoformat(),
        "directories_exist": {
            "twilio_audio": os.path.exists("twilio_audio"),
            "static/audio": os.path.exists("static/audio")
        }
    }

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if required environment variables are set
    required_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.info("Please check your .env file")
    else:
        logger.info("🚀 Starting AI Voice Bus System...")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
