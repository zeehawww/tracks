from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, JSONResponse
from typing import List, Dict
from pydantic import BaseModel
import random
import math
import datetime
import os
import requests
import re
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
from langdetect import detect
from fastapi import Form
from fastapi.responses import JSONResponse

class CallRequest(BaseModel):
    to_number: str

users_db = []

word_to_number = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10
}

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
NGROK_URL = os.getenv("NGROK_URL")  # added for Twilio callback
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# -------------------------------
# App setup
# -------------------------------
app = FastAPI()

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------------
# Root & favicon
# -------------------------------
@app.get("/")
def read_root():
    return {"message": "FastAPI is running!"}

@app.get("/favicon.ico")
async def favicon():
    favicon_path = os.path.join("static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return {"detail": "favicon not found"}

# -------------------------------
# Models
# -------------------------------
class Bus(BaseModel):
    bus_id: int
    route_id: int
    lat: float
    lon: float
    speed_kmph: float
    status: str
    overcrowded: bool
    next_stop_idx: int = 0
    eta_min: float = 0.0
    delayed: bool = False

class Stop(BaseModel):
    name: str
    lat: float
    lon: float
    scheduled_time: float

class Complaint(BaseModel):
    bus_id: int
    message: str
    timestamp: str

class SOSAlert(BaseModel):
    bus_id: int
    passenger_name: str
    emergency: str
    timestamp: str

class OvercrowdUpdate(BaseModel):
    overcrowded: bool

# -------------------------------
# Data storage
# -------------------------------
routes: Dict[int, List[Stop]] = {
    1: [
        Stop(name="Valasaravakkam", lat=13.0418, lon=80.1762, scheduled_time=0),
        Stop(name="Vadapalani", lat=13.0500, lon=80.2122, scheduled_time=5),
        Stop(name="Ramapuram", lat=13.0321, lon=80.1845, scheduled_time=10),
        Stop(name="Triplicane", lat=13.0604, lon=80.2824, scheduled_time=15),
        Stop(name="Porur", lat=13.0358, lon=80.1589, scheduled_time=20),
    ],
    2: [
        Stop(name="Koyambedu", lat=13.0732, lon=80.1800, scheduled_time=0),
        Stop(name="Anna Nagar", lat=13.0878, lon=80.2105, scheduled_time=5),
        Stop(name="Egmore", lat=13.0745, lon=80.2602, scheduled_time=10),
        Stop(name="Chintadripet", lat=13.0749, lon=80.2738, scheduled_time=15),
    ],
    3: [
        Stop(name="Guindy", lat=13.0106, lon=80.2206, scheduled_time=0),
        Stop(name="Saidapet", lat=13.0273, lon=80.2234, scheduled_time=5),
        Stop(name="Teynampet", lat=13.0441, lon=80.2518, scheduled_time=10),
        Stop(name="Mylapore", lat=13.0334, lon=80.2686, scheduled_time=15),
    ],
}

buses: List[Bus] = [
    Bus(bus_id=1, route_id=1, lat=13.0418, lon=80.1762, speed_kmph=40, status="On Route", overcrowded=False),
    Bus(bus_id=2, route_id=1, lat=13.0419, lon=80.1764, speed_kmph=35, status="On Route", overcrowded=True),
    Bus(bus_id=3, route_id=2, lat=13.0732, lon=80.1800, speed_kmph=30, status="On Route", overcrowded=False),
    Bus(bus_id=4, route_id=3, lat=13.0106, lon=80.2206, speed_kmph=45, status="On Route", overcrowded=True),
    Bus(bus_id=5, route_id=3, lat=13.0107, lon=80.2208, speed_kmph=50, status="On Route", overcrowded=False),
]

complaints: List[Complaint] = []
sos_alerts: List[SOSAlert] = []

landmarks = {
    "Koyambedu": "CMBT",
    "Vadapalani": "Forum Vijaya Mall",
    "Mylapore": "Kapaleeshwarar Temple",
    "Triplicane": "Parthasarathy Temple",
}

# -------------------------------
# Helper functions
# -------------------------------
def distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# -------------------------------
# Bus movement simulation
# -------------------------------
@app.post("/buses/update")
def update_buses():
    today = datetime.datetime.now().strftime("%A")
    for bus in buses:
        route = routes[bus.route_id]
        next_idx = bus.next_stop_idx
        next_stop = route[next_idx]
        lat_diff = next_stop.lat - bus.lat
        lon_diff = next_stop.lon - bus.lon
        bus.lat += lat_diff * 0.03
        bus.lon += lon_diff * 0.03
        if abs(lat_diff) < 0.0002 and abs(lon_diff) < 0.0002:
            bus.next_stop_idx = (bus.next_stop_idx + 1) % len(route)
        dist = distance(bus.lat, bus.lon, next_stop.lat, next_stop.lon)
        bus.eta_min = round((dist / max(bus.speed_kmph, 1)) * 60, 1)
        bus.delayed = random.choice([False, False, True])
        if today in ["Saturday", "Sunday"]:
            bus.delayed = True
            bus.eta_min += 5
        if today in ["Diwali", "Pongal"]:
            bus.delayed = True
            bus.eta_min += 10
    return {"message": "Buses updated"}

# -------------------------------
# Bus APIs
# -------------------------------
@app.get("/buses")
def get_all_buses():
    return {"buses": buses}

@app.get("/buses/{bus_id}")
def get_bus(bus_id: int):
    for bus in buses:
        if bus.bus_id == bus_id:
            return bus
    return {"error": "Bus not found"}

@app.get("/routes/{route_id}")
def get_route(route_id: int):
    stops = routes.get(route_id, [])
    for s in stops:
        if s.name in landmarks:
            s.name = landmarks[s.name]
    return {"stops": stops}

@app.patch("/buses/{bus_id}/overcrowded")
def update_overcrowded(bus_id: int, data: OvercrowdUpdate):
    for bus in buses:
        if bus.bus_id == bus_id:
            bus.overcrowded = data.overcrowded
            return {"message": f"Bus {bus_id} overcrowded set to {data.overcrowded}"}
    return {"error": "Bus not found"}

# -------------------------------
# Complaints & SOS
# -------------------------------
@app.post("/complaints")
def add_complaint(c: Complaint):
    complaints.append(c)
    return {"message": "Complaint registered", "total": len(complaints)}

@app.get("/complaints")
def list_complaints():
    return {"complaints": complaints}

@app.post("/sos")
def trigger_sos(s: SOSAlert):
    sos_alerts.append(s)
    return {"message": "SOS received", "total": len(sos_alerts)}

@app.get("/sos")
def list_sos():
    return {"sos": sos_alerts}

# -------------------------------
# Admin
# -------------------------------
@app.get("/admin/overview")
def admin_overview():
    today = datetime.datetime.now().strftime("%A")
    festival_delay = today in ["Diwali", "Pongal"]
    return {
        "active_buses": len(buses),
        "delayed": sum(1 for b in buses if b.delayed),
        "overcrowded": sum(1 for b in buses if b.overcrowded),
        "complaints": len(complaints),
        "sos": len(sos_alerts),
        "festival_delay": festival_delay,
    }

# -------------------------------
# AI Chat
# -------------------------------
@app.get("/ai_chat")
def ai_chat(query: str = Query(..., description="Ask about a bus, e.g., 'Where is bus 1?'")):
    query_lower = query.lower()
    match = re.search(r'\b(\d+)\b', query_lower)
    if match:
        bus_id = int(match.group())
        bus_info = next((b for b in buses if b.bus_id == bus_id), None)
        if bus_info:
            response = (
                f"Bus {bus_id} is currently {bus_info.status}. "
                f"Estimated arrival time at next stop is {bus_info.eta_min} minutes. "
                f"{'It is overcrowded.' if bus_info.overcrowded else 'It is not overcrowded.'}"
            )
        else:
            response = f"Sorry, no information found for bus {bus_id}."
    else:
        response = "I couldn't understand the bus number in your query. Please try again."
    return JSONResponse(content={"query": query, "response": response})

# -------------------------------
# Twilio Voice
# -------------------------------
@app.post("/voice")
async def handle_voice_call(request: Request):
    resp = VoiceResponse()
    gather = Gather(input="speech", action=f"{NGROK_URL}/process_speech", method="POST", timeout=5)

    gather.say("Welcome to Smart Bus Tracker. Please say your bus number now.")
    resp.append(gather)
    resp.say("Sorry, I did not receive any input. Goodbye!")
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process_speech")
async def process_speech(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult", "")
    print("🟢 Raw speech result from Twilio:", speech_result)

    resp = VoiceResponse()

    def nearest_stop(bus: Bus):
        route = routes[bus.route_id]
        nearest = min(route, key=lambda stop: distance(bus.lat, bus.lon, stop.lat, stop.lon))
        return landmarks.get(nearest.name, nearest.name)  # use landmark if available

    if speech_result:
        try:
            lang_code = detect(speech_result)
            print("🟢 Detected language:", lang_code)
            lang_map = {"en": "en-IN", "ta": "ta-IN", "hi": "hi-IN"}
            twilio_lang = lang_map.get(lang_code, "en-IN")

            bus_id = None
            match = re.search(r'\d+', speech_result)
            if match:
                bus_id = int(match.group())
            else:
                for w in speech_result.lower().split():
                    if w in word_to_number:
                        bus_id = word_to_number[w]
                        break
            print("🟢 Extracted bus_id:", bus_id)

            if bus_id is not None:
                bus_info = next((b for b in buses if b.bus_id == bus_id), None)
                if bus_info:
                    nearest = nearest_stop(bus_info)
                    message = (
                        f"Bus {bus_id} is currently {bus_info.status}, near {nearest}. "
                        f"Estimated arrival time at next stop is {bus_info.eta_min} minutes. "
                        f"{'It is overcrowded.' if bus_info.overcrowded else 'It is not overcrowded.'}"
                    )
                else:
                    message = f"Sorry, no information found for bus {bus_id}."
            else:
                message = "I didn't understand your bus number."
        except Exception as e:
            print("🔴 Exception in process_speech:", str(e))
            message = "I couldn't detect your language or fetch bus info."
            twilio_lang = "en-IN"
    else:
        print("🔴 No speech detected")
        message = "I didn't catch that. Goodbye!"
        twilio_lang = "en-IN"

    print("🟢 Final response to Twilio:", message)
    resp.say(message, language=twilio_lang)
    resp.hangup()
    return Response(content=str(resp), media_type="application/xml")


# -------------------------------
# Twilio call trigger from frontend
# -------------------------------
@app.post("/make_call")
async def make_call():
    if not NGROK_URL:
        return {"status": "error", "message": "NGROK_URL not set in .env"}

    to_number = os.getenv("VERIFIED_NUMBER")
    if not to_number:
        return {"status": "error", "message": "VERIFIED_NUMBER not set in .env"}

    try:
        call = twilio_client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{NGROK_URL}/voice"
        )
        return {"status": "calling", "call_sid": call.sid}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # Simple validation (replace with hashed pw check later)
    if not username or not password:
        return JSONResponse({"status": "error", "message": "Missing fields"}, status_code=400)

    # Save login info (you could store timestamp too)
    users_db.append({"username": username, "timestamp": datetime.datetime.now().isoformat()})

    return {"status": "success", "message": "Login successful", "user": username}
