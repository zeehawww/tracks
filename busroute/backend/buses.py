# backend/buses.py

from fastapi import APIRouter

router = APIRouter()

# Example bus data
bus_data = {
    1: {"route": "Alappakam -> Porur -> Kundrathur", "arrival_time": "10:30 AM", "departure_time": "10:35 AM", "delay": 5, "overcrowded": False},
    2: {"route": "Porur -> Kundrathur -> Alappakam", "arrival_time": "11:00 AM", "departure_time": "11:05 AM", "delay": 0, "overcrowded": True},
}

@router.get("/bus/{bus_id}")
def get_bus(bus_id: int):
    bus = bus_data.get(bus_id)
    if bus:
        return bus
    return {"error": "Bus not found"}
