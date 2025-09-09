import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const BASE = "http://127.0.0.1:8000";

// create a circular div icon with emoji + status color
const getBusIcon = (bus) => {
  let color = "#2ea44f";
  if (bus.delayed) color = "#ff8c00";
  if (bus.overcrowded) color = "#d73a49";
  const html = `
    <div style="
      background:${color};
      width:30px;
      height:30px;
      border-radius:15px;
      display:flex;
      align-items:center;
      justify-content:center;
      color:white;
      font-size:16px;
      box-shadow: 0 0 0 2px white;
    ">🚌</div>
  `;
  return L.divIcon({ html, className: "", iconSize: [30, 30], iconAnchor: [15, 15] });
};

function App() {
  const [buses, setBuses] = useState([]);
  const [searchId, setSearchId] = useState("");
  const [selectedBus, setSelectedBus] = useState(null);
  const [routeStops, setRouteStops] = useState([]);
  const [recentBuses, setRecentBuses] = useState(
    JSON.parse(localStorage.getItem("recentBuses")) || []
  );
  const [complaintText, setComplaintText] = useState("");
  const [adminStats, setAdminStats] = useState({});
  const [offlineMode, setOfflineMode] = useState(false);
  const [festivalAlert, setFestivalAlert] = useState(false);
  const [serviceAlerts, setServiceAlerts] = useState([]);

  const markersRef = useRef({});
  const mapRef = useRef(null);
  const selectedBusRef = useRef(null);

  useEffect(() => {
    selectedBusRef.current = selectedBus;
  }, [selectedBus]);

  // Polling
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
        // Go into Offline Mode
        setOfflineMode(true);
        const cached = JSON.parse(localStorage.getItem("lastBuses") || "[]");
        setBuses(cached);

        // If previously tracked bus, restore its cached route
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
      localStorage.setItem(`route_${routeId}`, JSON.stringify(res.data.stops || [])); // cache route
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
    } catch (err) {
      console.error("Failed to toggle overcrowded:", err);
    }
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
    if (!selectedBus || !complaintText) {
      alert("Select a bus and write a complaint first!");
      return;
    }
    await axios.post(`${BASE}/complaints`, {
      bus_id: selectedBus.bus_id,
      message: complaintText,
      timestamp: new Date().toISOString(),
    });
    alert("Complaint submitted ✅");
    setComplaintText("");
  };

  const triggerSOS = async () => {
    if (!selectedBus) {
      alert("Select a bus first to send SOS!");
      return;
    }
    await axios.post(`${BASE}/sos`, {
      bus_id: selectedBus.bus_id,
      passenger_name: "Anonymous",
      emergency: "Emergency reported from app",
      timestamp: new Date().toISOString(),
    });
    alert("🚨 SOS Sent!");
  };

  return (
    <div style={{ fontFamily: "Arial", backgroundColor: "#f4f8fc", minHeight: "100vh", padding: "1rem" }}>
      <h1 style={{ color: "#003366" }}>🚌 Chennai Real-Time Bus Tracker</h1>

      {/* Visual Alerts */}
      {offlineMode && <p style={{ color: "red", fontWeight: "bold" }}>⚠️ Offline Mode (cached data)</p>}
      {festivalAlert && <p style={{ color: "orange", fontWeight: "bold" }}>🎉 Festival Day! Expect delays 🚨</p>}
      {serviceAlerts.length > 0 && (
        <div style={{ background: "#fff3cd", padding: "0.5rem", borderRadius: "5px", marginBottom: "1rem" }}>
          <strong>📢 Service Alerts:</strong>
          <ul>
            {serviceAlerts.map((alert, idx) => (
              <li key={idx}>{alert}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Search */}
      <form onSubmit={handleSearch} style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem" }}>
        <input
          type="number"
          value={searchId}
          onChange={(e) => setSearchId(e.target.value)}
          placeholder="Enter Bus ID"
          style={{ padding: "0.5rem", flex: 1, borderRadius: "5px", border: "1px solid #003366" }}
        />
        <button type="submit" style={{ padding: "0.5rem 1rem", backgroundColor: "#003366", color: "#fff" }}>
          Track
        </button>
        <button type="button" onClick={clearTracking} style={{ padding: "0.5rem 1rem", backgroundColor: "#6c757d", color: "#fff" }}>
          Show All
        </button>
      </form>

      <div style={{ display: "flex", gap: "1rem" }}>
        {/* Map */}
        <MapContainer
          center={[13.0827, 80.2707]}
          zoom={12}
          style={{ height: "600px", width: "70%", borderRadius: "10px" }}
          whenCreated={(mapInstance) => (mapRef.current = mapInstance)}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; OSM & CARTO'
          />

          {selectedBus ? (
            <>
              <Polyline positions={routeStops.map((s) => [s.lat, s.lon])} color="#003366" weight={4} />
              <Marker
                key={selectedBus.bus_id}
                position={[selectedBus.lat, selectedBus.lon]}
                icon={getBusIcon(selectedBus)}
                ref={(ref) => { if (ref) markersRef.current[selectedBus.bus_id] = ref; }}
              >
                <Popup>
                  <strong>Bus {selectedBus.bus_id}</strong><br />
                  Status: {selectedBus.status} {selectedBus.delayed ? "🚨 Delayed" : ""}<br />
                  ETA next stop: {selectedBus.eta_min} min<br />
                  Overcrowded: {selectedBus.overcrowded ? "Yes" : "No"}<br />
                  Route: {routeStops.map((s) => s.name).join(" → ")}<br />
                  <div style={{ marginTop: 6 }}>
                    <button onClick={() => toggleOvercrowded(selectedBus.bus_id, selectedBus.overcrowded)}>
                      {selectedBus.overcrowded ? "Clear ✅" : "Mark 🚨"}
                    </button>
                    <button onClick={() => handleTrackFromPopup(selectedBus)}>Refresh & Track</button>
                  </div>
                </Popup>
              </Marker>
            </>
          ) : (
            buses.map((bus) => (
              <Marker
                key={bus.bus_id}
                position={[bus.lat, bus.lon]}
                icon={getBusIcon(bus)}
                ref={(ref) => { if (ref) markersRef.current[bus.bus_id] = ref; }}
              >
                <Popup>
                  <strong>Bus {bus.bus_id}</strong><br />
                  Route: {bus.route_id}<br />
                  Status: {bus.status} {bus.delayed ? "🚨 Delayed" : ""}<br />
                  ETA next stop: {bus.eta_min} min<br />
                  Overcrowded: {bus.overcrowded ? "Yes" : "No"}<br />
                  <div style={{ marginTop: 6 }}>
                    <button onClick={() => toggleOvercrowded(bus.bus_id, bus.overcrowded)}>
                      {bus.overcrowded ? "Clear ✅" : "Mark 🚨"}
                    </button>
                    <button onClick={() => handleTrackFromPopup(bus)}>Track This Bus</button>
                  </div>
                </Popup>
              </Marker>
            ))
          )}
        </MapContainer>

        {/* Right Panel */}
        <div style={{ width: "30%", backgroundColor: "#cce0ff", padding: "1rem", borderRadius: "10px" }}>
          {selectedBus ? (
            <>
              <h2 style={{ color: "#003366" }}>Bus Details</h2>
              <p><strong>Bus ID:</strong> {selectedBus.bus_id}</p>
              <p><strong>Route:</strong> {routeStops.map((s) => s.name).join(" → ")}</p>
              <p><strong>Status:</strong> {selectedBus.status} {selectedBus.delayed ? "🚨 Delayed" : ""}</p>
              <p><strong>ETA:</strong> {selectedBus.eta_min} min</p>
              <p><strong>Next Stop:</strong> {routeStops[selectedBus.next_stop_idx]?.name || "End"}</p>
              <div style={{ marginTop: "1rem" }}>
                <textarea
                  value={complaintText}
                  onChange={(e) => setComplaintText(e.target.value)}
                  placeholder="Write complaint..."
                  style={{ width: "100%", height: "60px" }}
                />
                <button onClick={submitComplaint} style={{ marginTop: "0.5rem", backgroundColor: "#d73a49", color: "white" }}>
                  Submit Complaint
                </button>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <button onClick={triggerSOS} style={{ backgroundColor: "#ff0000", color: "white", padding: "10px 20px" }}>
                  🚨 SOS
                </button>
              </div>
            </>
          ) : (
            <h2 style={{ color: "#003366" }}>Track a bus to see details</h2>
          )}

          {/* Recent */}
          <div style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "#fff", borderRadius: "10px" }}>
            <h3 style={{ color: "#003366" }}>🔮 Suggested for You</h3>
            {recentBuses.length > 0
              ? recentBuses.map((bus) => <p key={bus.bus_id}>Bus {bus.bus_id} → Route {bus.route_id}</p>)
              : <p>No recent buses tracked</p>}
          </div>

          {/* Admin Stats */}
          <div style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "#fff", borderRadius: "10px" }}>
            <h3 style={{ color: "#003366" }}>📊 Admin Overview</h3>
            <p>Active Buses: {adminStats.active_buses || 0}</p>
            <p>Delayed: {adminStats.delayed || 0}</p>
            <p>Overcrowded: {adminStats.overcrowded || 0}</p>
            <p>Complaints: {adminStats.complaints || 0}</p>
            <p>SOS Alerts: {adminStats.sos || 0}</p>
            {festivalAlert && <p>🎉 Festival Awareness: Expect Delays!</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
