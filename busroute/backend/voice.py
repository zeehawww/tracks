from fastapi import APIRouter, Request
from twilio.twiml.voice_response import VoiceResponse
import requests

router = APIRouter()

def get_bus_info(bus_id: str):
    url = f"http://127.0.0.1:8000/bus/{bus_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return f"Bus {bus_id} is at {data['location']} and will arrive in {data['eta']} minutes."
        return "Bus not found."
    except Exception as e:
        return f"Error: {str(e)}"

@router.post("/call")
async def voice_call(request: Request):
    form = await request.form()
    speech = form.get("SpeechResult", "").lower() if form.get("SpeechResult") else ""

    reply = "Welcome to the bus tracking system. Please say your bus number."
    if "bus" in speech:
        for word in speech.split():
            if word.isdigit():
                reply = get_bus_info(word)
                break

    vr = VoiceResponse()
    vr.say(reply, voice="alice", language="en-IN")
    return str(vr)
