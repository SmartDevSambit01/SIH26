import React, { useState } from "react";
import { Activity, X } from "lucide-react";

export function timeAgo(iso) {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

const STATUS_COLOR = {
  AVAILABLE: "#34D399",
  STALE: "#FBBF24",
};

function statusLine(entry) {
  if (!entry || !entry.status) return { text: "Loading…", color: "var(--c-muted)" };
  const age = timeAgo(entry.timestamp);
  return {
    text: `${entry.status}${age ? ` · ${age}` : ""}`,
    color: STATUS_COLOR[entry.status] || "#F87171",
  };
}

export default function SystemStatusPill({
  backendReachable = true,
  dataStatus,
}) {
  const [modalOpen, setModalOpen] = useState(false);

  const statusLabel = backendReachable ? "ONLINE" : "BACKEND UNREACHABLE";
  const rain = statusLine(dataStatus?.rainfall);
  const soil = statusLine(dataStatus?.soil_moisture);
  const sar = statusLine(dataStatus?.satellite);

  return (
    <>
      <div
        className={`system-status-pill ${backendReachable ? "online" : "offline"}`}
        onClick={() => setModalOpen(true)}
        style={{ cursor: "pointer" }}
        title="Click to view data pipeline & freshness status"
      >
        <div className="pulse-dot" />
        <span>{statusLabel}</span>
      </div>

      {modalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
          onClick={() => setModalOpen(false)}
        >
          <div
            style={{
              background: "var(--c-canvas-alt)",
              border: "1px solid var(--c-hairline)",
              borderRadius: "var(--r-md)",
              padding: 24,
              maxWidth: 540,
              width: "100%",
              color: "var(--c-white)",
              fontFamily: "var(--font-body)",
              boxShadow: "0 20px 50px rgba(0,0,0,0.6)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 16,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Activity size={20} color="var(--c-coral)" />
                <h3 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 600 }}>
                  Data Pipeline &amp; Freshness Status
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--c-muted)",
                  cursor: "pointer",
                }}
              >
                <X size={20} />
              </button>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
                fontSize: 13,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--c-hairline-soft)",
                  paddingBottom: 8,
                }}
              >
                <span style={{ color: "var(--c-muted)" }}>Backend Connection:</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: backendReachable ? "#4ade80" : "#f87171",
                  }}
                >
                  {statusLabel}
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--c-hairline-soft)",
                  paddingBottom: 8,
                }}
              >
                <span style={{ color: "var(--c-muted)" }}>
                  Terrain Baseline Source:
                </span>
                <span>SRTM DEM 30m Morphometry (Cached, Static)</span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--c-hairline-soft)",
                  paddingBottom: 8,
                }}
              >
                <span style={{ color: "var(--c-muted)" }}>
                  GPM Rainfall (NASA IMERG):
                </span>
                <span style={{ color: rain.color, fontWeight: 600 }}>
                  {rain.text}
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--c-hairline-soft)",
                  paddingBottom: 8,
                }}
              >
                <span style={{ color: "var(--c-muted)" }}>SMAP Soil Moisture:</span>
                <span style={{ color: soil.color, fontWeight: 600 }}>
                  {soil.text}
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--c-hairline-soft)",
                  paddingBottom: 8,
                }}
              >
                <span style={{ color: "var(--c-muted)" }}>
                  Sentinel-1 SAR Anomaly:
                </span>
                <span style={{ color: sar.color, fontWeight: 600 }}>
                  {sar.text}
                </span>
              </div>

              <div
                style={{
                  background: "rgba(255,255,255,0.04)",
                  padding: 12,
                  borderRadius: 8,
                  fontSize: 11.5,
                  lineHeight: 1.5,
                  color: "var(--c-muted)",
                  marginTop: 4,
                  border: "1px solid var(--c-hairline-soft)",
                }}
              >
                <strong>Honest Labeling Notice:</strong> In accordance with
                scientific integrity rules, this system never fabricates live
                values or misrepresents cached historical datasets as
                "real-time". Dynamic observations populate once NASA Earthdata
                credentials are configured.
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  marginTop: 10,
                }}
              >
                <button
                  onClick={() => setModalOpen(false)}
                  style={{
                    background: "var(--c-coral)",
                    border: "none",
                    color: "var(--c-canvas)",
                    padding: "6px 16px",
                    borderRadius: "var(--r-pill)",
                    fontFamily: "var(--font-body)",
                    fontWeight: 600,
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
