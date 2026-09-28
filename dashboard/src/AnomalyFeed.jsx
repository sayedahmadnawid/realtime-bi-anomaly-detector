const SEVERITY_COLORS = {
  medium: "#f59e0b",
  high: "#dc2626",
};

function formatRelative(isoString) {
  // detected_at is a real wall-clock timestamp (Postgres now()), so
  // comparing it against the browser's real "now" is meaningful - unlike
  // window_start/window_end, which are simulated business time and can be
  // days/weeks away from the real clock.
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffSec = Math.max(0, Math.round(diffMs / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  return `${diffHr}h ago`;
}

function formatWindow(isoStart, isoEnd) {
  const start = new Date(isoStart);
  const end = new Date(isoEnd);
  const opts = {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  };
  return `${start.toLocaleString([], opts)} \u2192 ${end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export default function AnomalyFeed({
  anomalies,
  severityFilter,
  onSeverityFilterChange,
}) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 16 }}>Live Anomaly Feed</h2>
        <select
          value={severityFilter}
          onChange={(e) => onSeverityFilterChange(e.target.value)}
        >
          <option value="">All severities</option>
          <option value="medium">Medium only</option>
          <option value="high">High only</option>
        </select>
      </div>

      {anomalies.length === 0 && (
        <p style={{ color: "#999", fontSize: 14 }}>
          No anomalies detected yet.
        </p>
      )}

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          maxHeight: 420,
          overflowY: "auto",
        }}
      >
        {anomalies.map((a, i) => {
          const color = SEVERITY_COLORS[a.severity] || "#666";
          const direction =
            a.actual_value < a.expected_value ? "\u2193" : "\u2191";
          return (
            <div
              key={`${a.metric}-${a.category}-${a.window_start}-${i}`}
              style={{
                border: `1px solid ${color}33`,
                borderLeft: `4px solid ${color}`,
                borderRadius: 6,
                padding: "8px 12px",
                background: `${color}0d`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 13,
                }}
              >
                <strong>
                  {a.metric}
                  {a.category ? ` \u00b7 ${a.category}` : " \u00b7 site-wide"}
                </strong>
                <span
                  style={{
                    color,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    fontSize: 11,
                  }}
                >
                  {a.severity}
                </span>
              </div>
              <div style={{ fontSize: 13, marginTop: 2 }}>
                {direction} expected {a.expected_value}, got{" "}
                <strong>{a.actual_value}</strong>
                {"  "}(z={a.z_score})
              </div>
              <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>
                {formatWindow(a.window_start, a.window_end)} &middot; detected{" "}
                {formatRelative(a.detected_at)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
