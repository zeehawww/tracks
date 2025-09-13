import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "./App.css";

const BASE = "http://127.0.0.1:8000";

const getBusIcon = (bus) => {
  let color = "#2ea44f";
  if (bus.delayed) color = "#ff8c00";
  if (bus.overcrowded) color = "#d73a49";
  const html = `
  <div class="bus-icon" style="background-color:${color}">🚌</div>
`;

  return L.divIcon({ html, className: "", iconSize: [30, 30], iconAnchor: [15, 15] });
};

function App() {
  const [buses, setBuses] = useState([]);
  const [searchId, setSearchId] = useState("");
  const [selectedBus, setSelectedBus] = useState(null);
  const [routeStops, setRouteStops] = useState([]);
  const [recentBuses, setRecentBuses] = useState(JSON.parse(localStorage.getItem("recentBuses")) || []);
  const [complaintText, setComplaintText] = useState("");
  const [adminStats, setAdminStats] = useState({});
  const [offlineMode, setOfflineMode] = useState(false);
  const [festivalAlert, setFestivalAlert] = useState(false);
  const [serviceAlerts, setServiceAlerts] = useState([]);
  const [aiQuery, setAiQuery] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const markersRef = useRef({});
  const mapRef = useRef(null);
  const selectedBusRef = useRef(null);
  const [callNumber, setCallNumber] = useState("");
  const [callStatus, setCallStatus] = useState("");

  useEffect(() => { selectedBusRef.current = selectedBus; }, [selectedBus]);

  // Polling buses & stats
  useEffect(() => {
    const poll = async () => {
      try {
        await axios.post(`${BASE}/buses/update`);
        const res = await axios.get(`${BASE}/buses`);
        setBuses(res.data.buses || []);
        localStorage.setItem("lastBuses", JSON.stringify(res.data.buses || []));
        setOfflineMode(false);

        if (selectedBusRef.current) {
          const r = await axios.get(`${BASE}/buses/${selectedBusRef.current.bus_id}`);
          setSelectedBus(r.data);
          const routeRes = await axios.get(`${BASE}/routes/${r.data.route_id}`);
          setRouteStops(routeRes.data.stops || []);
        }

        const stats = await axios.get(`${BASE}/admin/overview`);
        setAdminStats(stats.data);
        setFestivalAlert(stats.data.festival_delay || false);
        setServiceAlerts(stats.data.service_alerts || []);
      } catch (err) {
        setOfflineMode(true);
        const cached = JSON.parse(localStorage.getItem("lastBuses") || "[]");
        setBuses(cached);

        if (selectedBusRef.current) {
          const cachedRoute = JSON.parse(localStorage.getItem(`route_${selectedBusRef.current.route_id}`) || "[]");
          setRouteStops(cachedRoute);
        }
      }
    };

    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    buses.forEach((bus) => {
      const marker = markersRef.current[bus.bus_id];
      if (marker && marker.setLatLng) {
        marker.setLatLng([bus.lat, bus.lon]);
        marker.setIcon(getBusIcon(bus));
      }
    });
  }, [buses]);

  useEffect(() => {
    if (selectedBus && mapRef.current) {
      mapRef.current.flyTo([selectedBus.lat, selectedBus.lon], 15, { animate: true });
    }
  }, [selectedBus]);

  const fetchRoute = async (routeId) => {
    try {
      const res = await axios.get(`${BASE}/routes/${routeId}`);
      setRouteStops(res.data.stops || []);
      localStorage.setItem(`route_${routeId}`, JSON.stringify(res.data.stops || []));
    } catch {
      const cached = JSON.parse(localStorage.getItem(`route_${routeId}`) || "[]");
      setRouteStops(cached);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchId) return;
    try {
      const res = await axios.get(`${BASE}/buses/${searchId}`);
      setSelectedBus(res.data);
      await fetchRoute(res.data.route_id);
      const minimal = { bus_id: res.data.bus_id, route_id: res.data.route_id };
      const updated = [minimal, ...recentBuses.filter((b) => b.bus_id !== minimal.bus_id)].slice(0, 5);
      setRecentBuses(updated);
      localStorage.setItem("recentBuses", JSON.stringify(updated));
    } catch {
      alert("Bus not found!");
      setSelectedBus(null);
      setRouteStops([]);
    }
  };

  const clearTracking = () => {
    setSelectedBus(null);
    setRouteStops([]);
  };

  const toggleOvercrowded = async (busId, currentStatus) => {
    try {
      await axios.patch(`${BASE}/buses/${busId}/overcrowded`, { overcrowded: !currentStatus });
      const res = await axios.get(`${BASE}/buses`);
      setBuses(res.data.buses || []);
    } catch (err) { console.error(err); }
  };

  const handleTrackFromPopup = async (bus) => {
    setSelectedBus(bus);
    await fetchRoute(bus.route_id);
    const minimal = { bus_id: bus.bus_id, route_id: bus.route_id };
    const updated = [minimal, ...recentBuses.filter((b) => b.bus_id !== minimal.bus_id)].slice(0, 5);
    setRecentBuses(updated);
    localStorage.setItem("recentBuses", JSON.stringify(updated));
  };

  const submitComplaint = async () => {
    if (!selectedBus || !complaintText) return alert("Select a bus and write a complaint first!");
    await axios.post(`${BASE}/complaints`, {
      bus_id: selectedBus.bus_id,
      message: complaintText,
      timestamp: new Date().toISOString(),
    });
    alert("Complaint submitted ✅");
    setComplaintText("");
  };

  const triggerSOS = async () => {
    if (!selectedBus) return alert("Select a bus first to send SOS!");
    await axios.post(`${BASE}/sos`, {
      bus_id: selectedBus.bus_id,
      passenger_name: "Anonymous",
      emergency: "Emergency reported from app",
      timestamp: new Date().toISOString(),
    });
    alert("🚨 SOS Sent!");
  };

  const askAi = async (queryParam) => {
    const query = queryParam || aiQuery;
    if (!query) return;
    try {
      const res = await axios.get(`${BASE}/ai_chat`, { params: { query } });
      setAiResponse(res.data.response);
    } catch { setAiResponse("Failed to get a response."); }
  };

  const startListening = () => {
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) return alert("Speech Recognition not supported.");
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setAiQuery(transcript);
      setListening(false);
      askAi(transcript);
    };

    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  useEffect(() => {
    if (aiResponse) {
      const utterance = new SpeechSynthesisUtterance(aiResponse);
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }
  }, [aiResponse]);

  const makeCall = async () => {
    try {
      const res = await axios.post(`${BASE}/make_call`);
      if (res.data.status === "calling") {
        setCallStatus(`Calling your verified number... Call SID: ${res.data.call_sid}`);
      } else {
        setCallStatus(`Error: ${res.data.message}`);
      }
    } catch {
      setCallStatus("Failed to make call.");
    }
  };
  

  return (
    <div className="app-container">
      <h1>🚌 Chennai Real-Time Bus Tracker</h1>

      <div className="alerts">
        {offlineMode && <p className="alert offline">⚠️ Offline Mode (cached data)</p>}
        {festivalAlert && <p className="alert festival">🎉 Festival Day! Expect delays 🚨</p>}
        {serviceAlerts.length > 0 && (
          <div className="panel">
            <strong>📢 Service Alerts:</strong>
            <ul>{serviceAlerts.map((a, i) => <li key={i}>{a}</li>)}</ul>
          </div>
        )}
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <input type="number" value={searchId} onChange={(e) => setSearchId(e.target.value)} placeholder="Enter Bus ID" />
        <button type="submit" className="primary-btn">Track</button>
        <button type="button" className="secondary-btn" onClick={clearTracking}>Show All</button>
      </form>

      <div className="main-content">
        <MapContainer center={[13.0827, 80.2707]} zoom={12} className="map-container" whenCreated={(m) => mapRef.current = m}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" attribution='&copy; OSM & CARTO' />

          {selectedBus ? (
            <>
              <Polyline positions={routeStops.map(s => [s.lat, s.lon])} color="#003366" weight={4} />
              <Marker key={selectedBus.bus_id} position={[selectedBus.lat, selectedBus.lon]} icon={getBusIcon(selectedBus)} ref={r => { if (r) markersRef.current[selectedBus.bus_id] = r; }}>
                <Popup>
                  <strong>Bus {selectedBus.bus_id}</strong><br/>
                  Status: {selectedBus.status} {selectedBus.delayed ? "🚨 Delayed" : ""}<br/>
                  ETA next stop: {selectedBus.eta_min} min<br/>
                  Overcrowded: {selectedBus.overcrowded ? "Yes" : "No"}<br/>
                  Route: {routeStops.map(s => s.name).join(" → ")}<br/>
                  <div className="popup-buttons">
                    <button onClick={() => toggleOvercrowded(selectedBus.bus_id, selectedBus.overcrowded)}>
                      {selectedBus.overcrowded ? "Clear ✅" : "Mark 🚨"}
                    </button>
                    <button onClick={() => handleTrackFromPopup(selectedBus)}>Refresh & Track</button>
                  </div>
                </Popup>
              </Marker>
            </>
          ) : buses.map(bus => (
            <Marker key={bus.bus_id} position={[bus.lat, bus.lon]} icon={getBusIcon(bus)} ref={r => { if (r) markersRef.current[bus.bus_id] = r; }}>
              <Popup>
                <strong>Bus {bus.bus_id}</strong><br/>
                Route: {bus.route_id}<br/>
                Status: {bus.status} {bus.delayed ? "🚨 Delayed" : ""}<br/>
                ETA next stop: {bus.eta_min} min<br/>
                Overcrowded: {bus.overcrowded ? "Yes" : "No"}<br/>
                <div className="popup-buttons">
                  <button onClick={() => toggleOvercrowded(bus.bus_id, bus.overcrowded)}>
                    {bus.overcrowded ? "Clear ✅" : "Mark 🚨"}
                  </button>
                  <button onClick={() => handleTrackFromPopup(bus)}>Track This Bus</button>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        <div className="right-panel">
          {selectedBus && (
            <div className="panel">
              <h2>Bus Details</h2>
              <p><strong>Bus ID:</strong> {selectedBus.bus_id}</p>
              <p><strong>Route:</strong> {routeStops.map(s => s.name).join(" → ")}</p>
              <p><strong>Status:</strong> {selectedBus.status} {selectedBus.delayed ? "🚨 Delayed" : ""}</p>
              <p><strong>ETA:</strong> {selectedBus.eta_min} min</p>
              <p><strong>Next Stop:</strong> {routeStops[selectedBus.next_stop_idx]?.name || "End"}</p>
              <textarea value={complaintText} onChange={(e) => setComplaintText(e.target.value)} placeholder="Write complaint..." />
              <button className="complaint-btn" onClick={submitComplaint}>Submit Complaint</button>
              <button className="sos-btn" onClick={triggerSOS}>🚨 SOS</button>
            </div>
          )}

          <div className="panel">
            <h3>🔮 Suggested for You</h3>
            {recentBuses.length > 0 ? recentBuses.map(bus => <p key={bus.bus_id}>Bus {bus.bus_id} → Route {bus.route_id}</p>) : <p>No recent buses tracked</p>}
          </div>

         

          <div className="panel">
            <h3>🤖 AI Bus Assistant</h3>
            <input type="text" value={aiQuery} onChange={(e) => setAiQuery(e.target.value)} placeholder="Ask about a bus, e.g., 'Where is bus 1?'" />
            <div className="ai-buttons">
              <button onClick={() => askAi()} className="primary-btn">Ask AI</button>
              <button onClick={startListening} className="secondary-btn">{listening ? "🎙️ Listening..." : "🎤 Speak"}</button>
            </div>
            {aiResponse && <p className="ai-response">{aiResponse}</p>}
          </div>

          <div className="panel">
            <h3>📞 Call Bus Tracker</h3>
            <button className="primary-btn" onClick={makeCall}>Call</button>
            {callStatus && <p>{callStatus}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 