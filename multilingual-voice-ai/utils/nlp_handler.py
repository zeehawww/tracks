from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Initialize NLP models (simplified approach using rule-based + BERT)
try:
    # Load a general classification model (you can fine-tune this for Indian languages)
    sentiment_pipeline = pipeline("sentiment-analysis", return_all_scores=True)
    logger.info("🧠 NLP models loaded")
except Exception as e:
    logger.error(f"❌ Error loading NLP models: {e}")
    sentiment_pipeline = None

async def extract_intent_and_entities(text: str, language: str) -> Tuple[str, Dict]:
    """
    Extract intent and entities from transcribed text
    Returns: (intent, entities_dict)
    """
    try:
        text_lower = text.lower()
        
        # Define patterns for different intents (expandable)
        intent_patterns = {
            "bus_timings": [
                r"bus.*time", r"timing", r"schedule", r"kab.*bus", r"time.*bus",
                r"समय", r"बस.*कब", r"timing", r"schedule"
            ],
            "bus_route": [
                r"route", r"path", r"way", r"jaana", r"rasta", r"कैसे जाऊं",
                r"route", r"रास्ता", r"मार्ग"
            ],
            "bus_arrival": [
                r"arrive", r"reach", r"aa.*rahi", r"coming", r"आ.*रही", 
                r"पहुंच", r"arrive"
            ],
            "complaint": [
                r"problem", r"issue", r"complaint", r"परेशानी", r"समस्या", 
                r"शिकायत"
            ],
            "fare": [
                r"fare", r"price", r"cost", r"kitna.*paisa", r"कितना.*पैसा",
                r"किराया", r"दाम"
            ]
        }
        
        # Extract entities (locations, numbers, etc.)
        entities = {}
        
        # Extract locations (simple approach)
        location_keywords = [
            "big bazaar", "forum mall", "brigade road", "mg road", "majestic",
            "electronic city", "whitefield", "koramangala", "indiranagar",
            "marathahalli", "silk board", "btm layout", "jayanagar"
        ]
        
        for location in location_keywords:
            if location in text_lower:
                entities["location"] = location
                break
        
        # Extract time mentions
        time_patterns = [
            r"(\d{1,2}):(\d{2})", r"(\d{1,2})\s*(am|pm)", r"(\d{1,2})\s*baje",
            r"(\d{1,2})\s*minute", r"(\d{1,2})\s*min"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["time"] = match.group()
                break
        
        # Extract bus numbers
        bus_number_pattern = r"bus\s*(\d+[a-zA-Z]*)"
        bus_match = re.search(bus_number_pattern, text_lower)
        if bus_match:
            entities["bus_number"] = bus_match.group(1)
        
        # Determine intent
        detected_intent = "general_inquiry"  # default
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected_intent = intent
                    break
            if detected_intent != "general_inquiry":
                break
        
        logger.info(f"🎯 Intent: {detected_intent}, Entities: {entities}")
        return detected_intent, entities
        
    except Exception as e:
        logger.error(f"❌ NLP processing error: {e}")
        return "general_inquiry", {}
