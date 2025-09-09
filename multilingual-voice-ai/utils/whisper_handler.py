import whisper
import torch
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

# Load Whisper model globally (loaded once)
try:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model("base", device=device)  # Use "large-v3" for better accuracy
    logger.info(f"🤖 Whisper model loaded on {device}")
except Exception as e:
    logger.error(f"❌ Error loading Whisper model: {e}")
    model = None

async def transcribe_audio(audio_path: str):
    """
    Transcribe audio file using Whisper
    Returns: (transcript_text, detected_language)
    """
    try:
        if not model:
            raise Exception("Whisper model not loaded")
        
        # Run transcription in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: model.transcribe(
                audio_path, 
                language=None,  # Auto-detect language
                fp16=torch.cuda.is_available()
            )
        )
        
        transcript = result["text"].strip()
        detected_language = result["language"]
        
        # Map whisper language codes to our system
        lang_mapping = {
            "hi": "hindi",
            "en": "english", 
            "te": "telugu",
            "ta": "tamil",
            "kn": "kannada"
        }
        
        language = lang_mapping.get(detected_language, "english")
        
        logger.info(f"📝 Transcription: '{transcript}' (Language: {language})")
        return transcript, language
        
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        # Fallback
        return "मुझे समझ नहीं आया, कृपया दोबारा बोलिए", "hindi"
