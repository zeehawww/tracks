import logging
from typing import Dict, Tuple
import random

logger = logging.getLogger(__name__)

# Sample bus data (replace with real API/database calls)
SAMPLE_BUS_DATA = {
    "routes": {
        "big bazaar": {
            "buses": ["22C", "45", "102"],
            "timings": ["10:30", "11:00", "11:30", "12:00", "12:30"],
            "fare": 15
        },
        "forum mall": {
            "buses": ["201", "500C", "G1"],
            "timings": ["10:15", "10:45", "11:15", "11:45", "12:15"],
            "fare": 20
        },
        "mg road": {
            "buses": ["101", "201", "301"],
            "timings": ["10:00", "10:20", "10:40", "11:00", "11:20"],
            "fare": 12
        }
    }
}

async def get_bus_info_response(intent: str, entities: Dict, language: str) -> Tuple[str, str]:
    """
    Generate response based on intent and entities
    Returns: (response_text, language_code)
    """
    try:
        location = entities.get("location", "")
        bus_number = entities.get("bus_number", "")
        time_mentioned = entities.get("time", "")
        
        # Generate response based on intent
        if intent == "bus_timings":
            response = await get_timing_response(location, language)
        elif intent == "bus_route":
            response = await get_route_response(location, language)
        elif intent == "bus_arrival":
            response = await get_arrival_response(location, language)
        elif intent == "fare":
            response = await get_fare_response(location, language)
        elif intent == "complaint":
            response = await get_complaint_response(language)
        else:
            response = await get_general_response(language)
        
        return response, language
        
    except Exception as e:
        logger.error(f"❌ Business logic error: {e}")
        return get_error_response(language), language

async def get_timing_response(location: str, language: str) -> str:
    """Get bus timing information"""
    if location in SAMPLE_BUS_DATA["routes"]:
        route_data = SAMPLE_BUS_DATA["routes"][location]
        next_timing = random.choice(route_data["timings"])
        bus = random.choice(route_data["buses"])
        
        if language == "hindi":
            return f"हाँ, {location} से अगली बस {bus} नंबर {next_timing} बजे आएगी। शुभ यात्रा!"
        else:
            return f"Yes, the next bus {bus} from {location} will arrive at {next_timing}. Have a safe journey!"
    else:
        if language == "hindi":
            return f"माफ करिए, {location} के बारे में जानकारी अभी उपलब्ध नहीं है। कृपया दूसरी जगह बताइए।"
        else:
            return f"Sorry, information about {location} is not available right now. Please try another location."

async def get_arrival_response(location: str, language: str) -> str:
    """Get bus arrival information"""
    if location in SAMPLE_BUS_DATA["routes"]:
        minutes = random.choice([2, 3, 5, 7, 10])
        bus = random.choice(SAMPLE_BUS_DATA["routes"][location]["buses"])
        
        if language == "hindi":
            return f"हाँ, बस {bus} नंबर अभी {minutes} मिनट में {location} पहुंचने वाली है।"
        else:
            return f"Yes, bus number {bus} will reach {location} in {minutes} minutes."
    else:
        if language == "hindi":
            return "माफ करिए, इस समय बस की सटीक जानकारी उपलब्ध नहीं है।"
        else:
            return "Sorry, exact bus information is not available at this time."

async def get_route_response(location: str, language: str) -> str:
    """Get route information"""
    if language == "hindi":
        return f"{location} जाने के लिए मेट्रो स्टेशन से बस नंबर 101, 201, या 301 ले सकते हैं।"
    else:
        return f"To go to {location}, you can take bus number 101, 201, or 301 from the metro station."

async def get_fare_response(location: str, language: str) -> str:
    """Get fare information"""
    if location in SAMPLE_BUS_DATA["routes"]:
        fare = SAMPLE_BUS_DATA["routes"][location]["fare"]
        if language == "hindi":
            return f"{location} का किराया {fare} रुपए है।"
        else:
            return f"The fare to {location} is {fare} rupees."
    else:
        if language == "hindi":
            return "सामान्यतः किराया 10 से 25 रुपए के बीच होता है।"
        else:
            return "Generally, the fare ranges between 10 to 25 rupees."

async def get_complaint_response(language: str) -> str:
    """Handle complaints"""
    if language == "hindi":
        return "आपकी शिकायत दर्ज हो गई है। हमारी टीम जल्दी ही इसपर कार्रवाई करेगी। धन्यवाद!"
    else:
        return "Your complaint has been registered. Our team will take action on it soon. Thank you!"

async def get_general_response(language: str) -> str:
    """General response"""
    if language == "hindi":
        return "मैं बस की जानकारी देने में आपकी मदद कर सकता हूँ। बस का समय, रूट, या किराया जानना चाहते हैं?"
    else:
        return "I can help you with bus information. Would you like to know about bus timings, routes, or fare?"

def get_error_response(language: str) -> str:
    """Error response"""
    if language == "hindi":
        return "माफ करिए, कुछ समस्या हुई है। कृपया दोबारा कोशिश करें।"
    else:
        return "Sorry, there was some issue. Please try again."
