from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict
from pydantic import BaseModel
import random
import math
import datetime
import os

# Correct imports assuming `backend` is the package
from . import buses, voice  # use relative imports inside a package

app = FastAPI()
app.include_router(buses.router)
app.include_router(voice.router)

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    scheduled_time: float  # minutes from start


class Complaint(BaseModel):
    bus_id: int
    message: str
    timestamp: str


class SOSAlert(BaseModel):
    bus_id: int
    passenger_name: str
    emergency: str
    timestamp: str

# -------------------------------
# Routes Data
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

# -------------------------------
# Predefined buses
# -------------------------------
buses: List[Bus] = [
    Bus(bus_id=1, route_id=1, lat=13.0418, lon=80.1762, speed_kmph=40, status="On Route", overcrowded=False),
    Bus(bus_id=2, route_id=1, lat=13.0419, lon=80.1764, speed_kmph=35, status="On Route", overcrowded=True),
    Bus(bus_id=3, route_id=2, lat=13.0732, lon=80.1800, speed_kmph=30, status="On Route", overcrowded=False),
    Bus(bus_id=4, route_id=3, lat=13.0106, lon=80.2206, speed_kmph=45, status="On Route", overcrowded=True),
    Bus(bus_id=5, route_id=3, lat=13.0107, lon=80.2208, speed_kmph=50, status="On Route", overcrowded=False),
]

# Storage
complaints: List[Complaint] = []
sos_alerts: List[SOSAlert] = []

landmarks = {
    "Koyambedu": "CMBT",
    "Vadapalani": "Forum Vijaya Mall",
    "Mylapore": "Kapaleeshwarar Temple",
    "Triplicane": "Parthasarathy Temple",
}

# -------------------------------
# Helpers
# -------------------------------
def distance(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# -------------------------------
# Routes for updating & fetching buses
# -------------------------------
# ... keep the rest of your APIs unchanged



# -------------------------------
# Update bus positions (simulate movement)
# -------------------------------
@app.post("/buses/update")
def update_buses():
    today = datetime.datetime.now().strftime("%A")
    for bus in buses:
        route = routes[bus.route_id]
        next_idx = bus.next_stop_idx
        next_stop = route[next_idx]

        # Move bus towards next stop
        lat_diff = next_stop.lat - bus.lat
        lon_diff = next_stop.lon - bus.lon
        bus.lat += lat_diff * 0.03
        bus.lon += lon_diff * 0.03

        # Reached stop
        if abs(lat_diff) < 0.0002 and abs(lon_diff) < 0.0002:
            bus.next_stop_idx = (bus.next_stop_idx + 1) % len(route)

        # ETA calculation
        dist = distance(bus.lat, bus.lon, next_stop.lat, next_stop.lon)
        bus.eta_min = round((dist / max(bus.speed_kmph, 1)) * 60, 1)

        # Random delays
        bus.delayed = random.choice([False, False, True])

        # Weekend/festival delays
        if today in ["Saturday", "Sunday"]:
            bus.delayed = True
            bus.eta_min += 5
        if today in ["Diwali", "Pongal"]:  # placeholder
            bus.delayed = True
            bus.eta_min += 10

    return {"message": "Buses updated"}


# -------------------------------
# APIs
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
    # apply landmark aliases
    for s in stops:
        if s.name in landmarks:
            s.name = landmarks[s.name]
    return {"stops": stops}


class OvercrowdUpdate(BaseModel):
    overcrowded: bool


@app.patch("/buses/{bus_id}/overcrowded")
def update_overcrowded(bus_id: int, data: OvercrowdUpdate):
    for bus in buses:
        if bus.bus_id == bus_id:
            bus.overcrowded = data.overcrowded
            return {"message": f"Bus {bus_id} overcrowded set to {data.overcrowded}"}
    return {"error": "Bus not found"}


# Complaints & SOS
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


# Admin Dashboard
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


# Offline cache API
@app.get("/offline/cache")
def offline_cache():
    return {"buses": buses, "routes": routes}
