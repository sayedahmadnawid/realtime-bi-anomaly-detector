import { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const METRICS = ["orders", "revenue", "traffic", "signups", "inventory_level"];
const CATEGORIES = ["", "electronics", "home_kitchen", "apparel"];
const POLL_INTERVAL_MS = 3000;
const POINTS_TO_SHOW = 100;

function formatTime(isoString) {
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function App() {
  const [metric, setMetric] = useState("orders");
  const [category, setCategory] = useState("electronics");
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchEvents = useCallback(async () => {
    const params = new URLSearchParams({ metric, limit: String(POINTS_TO_SHOW) });
    if (category) params.set("category", category);

    try {
      const res = await fetch(`${API_BASE}/events?${params.toString()}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const rows = await res.json();
      // API returns most-recent-first; chart wants chronological order.
      const chronological = [...rows].reverse().map((r) => ({
        ...r,
        label: formatTime(r.event_time),
      }));
      setData(chronological);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e.message);
    }
  }, [metric, category]);

  useEffect(() => {
    fetchEvents();
    const id = setInterval(fetchEvents, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchEvents]);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "24px", maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 4 }}>NovaCart BI Dashboard</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        Live view of simulated business metrics · polling every {POLL_INTERVAL_MS / 1000}s
      </p>

      <div style={{ display: "flex", gap: 16, marginBottom: 16, alignItems: "center" }}>
        <label>
          Metric:{" "}
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {METRICS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>

        <label>
          Category:{" "}
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c === "" ? "(site-wide)" : c}</option>
            ))}
          </select>
        </label>

        {lastUpdated && (
          <span style={{ color: "#999", fontSize: 13 }}>
            Last updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      {error && (
        <div style={{ color: "#b00020", marginBottom: 16 }}>
          Error loading data: {error}
        </div>
      )}

      {!error && data.length === 0 && <p>Loading…</p>}

      {data.length > 0 && (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" minTickGap={30} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              name={`${metric}${category ? " (" + category + ")" : ""}`}
              stroke="#4ab332"
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}