import { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import AnomalyFeed from "./Anomalyfeed";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const METRICS = ["orders", "revenue", "traffic", "signups", "inventory_level", "payment_attempts", "payment_failures"];
const CATEGORIES = ["", "electronics", "home_kitchen", "apparel"];
const POLL_INTERVAL_MS = 3000;
const POINTS_TO_SHOW = 150;

const SEVERITY_COLORS = { medium: "#f59e0b", high: "#dc2626" };

function formatTimeTick(ms) {
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function App() {
  const [metric, setMetric] = useState("orders");
  const [category, setCategory] = useState("electronics");
  const [data, setData] = useState([]);
  const [chartAnomalies, setChartAnomalies] = useState([]);   // anomalies matching current metric/category, for overlay
  const [feedAnomalies, setFeedAnomalies] = useState([]);      // all recent anomalies, for the live feed
  const [feedSeverity, setFeedSeverity] = useState("");
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchAll = useCallback(async () => {
    const eventParams = new URLSearchParams({ metric, limit: String(POINTS_TO_SHOW) });
    if (category) eventParams.set("category", category);

    const chartAnomalyParams = new URLSearchParams({ metric, limit: "20" });
    if (category) chartAnomalyParams.set("category", category);

    const feedParams = new URLSearchParams({ limit: "20" });
    if (feedSeverity) feedParams.set("severity", feedSeverity);

    try {
      const [eventsRes, chartAnomRes, feedRes] = await Promise.all([
        fetch(`${API_BASE}/events?${eventParams}`),
        fetch(`${API_BASE}/anomalies?${chartAnomalyParams}`),
        fetch(`${API_BASE}/anomalies?${feedParams}`),
      ]);

      if (!eventsRes.ok) throw new Error(`/events HTTP ${eventsRes.status}`);
      if (!chartAnomRes.ok) throw new Error(`/anomalies HTTP ${chartAnomRes.status}`);
      if (!feedRes.ok) throw new Error(`/anomalies (feed) HTTP ${feedRes.status}`);

      const eventsRows = await eventsRes.json();
      const chartAnomRows = await chartAnomRes.json();
      const feedRows = await feedRes.json();

      // API returns most-recent-first; chart wants chronological order,
      // and needs a numeric time field so ReferenceArea can align to it.
      const chronological = [...eventsRows].reverse().map((r) => ({
        time: new Date(r.event_time).getTime(),
        value: r.value,
      }));

      setData(chronological);
      setChartAnomalies(chartAnomRows);
      setFeedAnomalies(feedRows);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e.message);
    }
  }, [metric, category, feedSeverity]);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchAll]);

  const timeDomain =
    data.length > 0 ? [data[0].time, data[data.length - 1].time] : ["dataMin", "dataMax"];

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "24px", maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 4 }}>NovaCart BI Dashboard</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        Live view of simulated business metrics · polling every {POLL_INTERVAL_MS / 1000}s
      </p>

      <div style={{ display: "flex", gap: 16, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
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
        <div style={{ color: "#b00020", marginBottom: 16 }}>Error loading data: {error}</div>
      )}

      {!error && data.length === 0 && <p>Loading…</p>}

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, alignItems: "start" }}>
        {data.length > 0 && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                type="number"
                domain={timeDomain}
                tickFormatter={formatTimeTick}
                scale="time"
              />
              <YAxis />
              <Tooltip labelFormatter={(ms) => new Date(ms).toLocaleString()} />
              <Legend />

              {chartAnomalies.map((a, i) => {
                const x1 = new Date(a.window_start).getTime();
                const x2 = new Date(a.window_end).getTime();
                const color = SEVERITY_COLORS[a.severity] || "#666";
                return (
                  <ReferenceArea
                    key={`${a.window_start}-${i}`}
                    x1={x1}
                    x2={x2}
                    stroke={color}
                    strokeOpacity={0.6}
                    fill={color}
                    fillOpacity={0.15}
                    label={{ value: a.severity, position: "insideTop", fill: color, fontSize: 10 }}
                  />
                );
              })}

              <Line
                type="monotone"
                dataKey="value"
                name={`${metric}${category ? " (" + category + ")" : ""}`}
                stroke="#2563eb"
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        <AnomalyFeed
          anomalies={feedAnomalies}
          severityFilter={feedSeverity}
          onSeverityFilterChange={setFeedSeverity}
        />
      </div>
    </div>
  );
}