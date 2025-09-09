import torch
from transformers import AutoModel, AutoTokenizer
import soundfile as sf
import logging
import os
import uuid
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# Global TTS model
tts_model = None
tts_tokenizer = None

try:
    # Load AI4Bharat VITS model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tts_model = AutoModel.from_pretrained("ai4bharat/vits_rasa_13", trust_remote_code=True).to(device)
    tts_tokenizer = AutoTokenizer.from_pretrained("ai4bharat/vits_rasa_13", trust_remote_code=True)
    logger.info(f"🔊 TTS model loaded on {device}")
except Exception as e:
    logger.error(f"❌ Error loading TTS model: {e}")
    tts_model = None

async def generate_speech(text: str, language: str, base_url: str) -> str:
    """
    Generate speech audio from text
    Returns: URL to the generated audio file
    """
    try:
        if not tts_model:
            logger.warning("TTS model not available, using fallback")
            return create_fallback_audio(text, base_url)
        
        # Choose speaker and style based on language
        speaker_mapping = {
            "hindi": {"speaker_id": 16, "emotion_id": 0},  # PAN_M, ALEXA style
            "english": {"speaker_id": 8, "emotion_id": 0},
            "default": {"speaker_id": 16, "emotion_id": 0}
        }
        
        config = speaker_mapping.get(language, speaker_mapping["default"])
        
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        filename = f"response_{audio_id}.wav"
        filepath = os.path.join("static", "audio", filename)
        
        # Run TTS in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: generate_tts_sync(text, config, filepath)
        )
        
        # Return URL for Twilio to access
        audio_url = f"{base_url.rstrip('/')}/static/audio/{filename}"
        logger.info(f"🔊 Audio generated: {audio_url}")
        return audio_url
        
    except Exception as e:
        logger.error(f"❌ TTS generation error: {e}")
        return create_fallback_audio(text, base_url)

def generate_tts_sync(text: str, config: dict, filepath: str):
    """Synchronous TTS generation"""
    try:
        inputs = tts_tokenizer(text=text, return_tensors="pt").to(tts_model.device)
        
        with torch.no_grad():
            outputs = tts_model(
                inputs['input_ids'],
                speaker_id=config["speaker_id"],
                emotion_id=config["emotion_id"]
            )
        
        # Save audio
        audio = outputs.waveform.squeeze().cpu().numpy()
        sf.write(filepath, audio, tts_model.config.sampling_rate)
        
        logger.info(f"✅ TTS audio saved: {filepath}")
        
    except Exception as e:
        logger.error(f"❌ Sync TTS error: {e}")
        raise

def create_fallback_audio(text: str, base_url: str) -> str:
    """Create a simple fallback when TTS fails"""
    try:
        # For demo purposes, create a simple tone (replace with actual TTS service)
        import numpy as np
        
        # Generate a simple beep sound as placeholder
        duration = min(len(text) * 0.1, 5.0)  # Max 5 seconds
        sample_rate = 22050
        t = np.linspace(0, duration, int(sample_rate * duration))
        frequency = 440  # A4 note
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Save as WAV
        audio_id = str(uuid.uuid4())
        filename = f"fallback_{audio_id}.wav"
        filepath = os.path.join("static", "audio", filename)
        
        sf.write(filepath, audio, sample_rate)
        
        audio_url = f"{base_url.rstrip('/')}/static/audio/{filename}"
        logger.info(f"🔊 Fallback audio created: {audio_url}")
        return audio_url
        
    except Exception as e:
        logger.error(f"❌ Fallback audio error: {e}")
        # Return empty string to use TTS only
        return ""
