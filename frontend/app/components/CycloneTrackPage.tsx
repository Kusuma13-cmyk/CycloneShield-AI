"use client";
/**
 * Cyclone Track page — shows the track on a Leaflet map + intensity chart.
 * Leaflet is dynamically imported (no SSR) because it requires window.
 */
import type { AnalysisSession, TrackPoint } from "../../lib/api";
import { useEffect, useState } from "react";
import { fetchTrack } from "../../lib/api";
import dynamic from "next/dynamic";
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";

// Dynamically import the map so it only renders client-side
const CycloneMap = dynamic(() => import("./CycloneMap"), { ssr: false });

interface Props { session: AnalysisSession | null; }

const INTENSITY_COLORS: Record<string, string> = {
  "Depression": "#AED6F1",
  "Deep Depression": "#85C1E9",
  "Cyclonic Storm": "#F1C40F",
  "Severe Cyclonic Storm": "#E67E22",
  "Very Severe Cyclonic Storm": "#E74C3C",
  "Extremely Severe Cyclonic Storm": "#922B21",
  "Super Cyclonic Storm": "#6C0000",
};

export default function CycloneTrackPage({ session }: Props) {
  const [track, setTrack] = useState<TrackPoint[]>([]);
  const [loadingTrack, setLoadingTrack] = useState(false);
  const [trackError, setTrackError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingTrack(true);
    fetchTrack()
      .then((r) => setTrack(r.track))
      .catch((e) => setTrackError(e.message))
      .finally(() => setLoadingTrack(false));
  }, []);

  const latest = track.length > 0 ? track[track.length - 1] : null;

  // Build chart data — wind + pressure over time
  const chartData = track.map((p) => ({
    time: p.timestamp.slice(5, 16).replace("T", " "),
    wind: p.wind_speed_kmh,
    pressure: p.pressure_hpa,
    intensity: p.intensity_category,
  }));

  return (
    <div>
      <div className="section-header">🗺️ Cyclone Track Map</div>
      {(session?.provider_name === "demo" || session?.data_mode === "sample") && (
        <div className="demo-banner">
          ⚠️ <strong>DEMO / SAMPLE DATA</strong> — This track is synthetic test data.
          It is <strong>not</strong> a real cyclone track or an official IMD advisory.
        </div>
      )}

      {latest && (
        <div className="card-grid" style={{ marginBottom: 16 }}>
          {[
            { label: "Storm", value: latest.storm_name },
            { label: "Intensity", value: latest.intensity_category.split(" ").pop() ?? latest.intensity_category },
            { label: "Wind", value: `${latest.wind_speed_kmh} km/h` },
            { label: "Track Points", value: String(track.length) },
          ].map((m) => (
            <div key={m.label} className="metric-card">
              <div className="metric-label">{m.label}</div>
              <div className="metric-value" style={{ fontSize: "1.1em" }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Map */}
      {loadingTrack ? (
        <div className="spinner-wrap"><div className="spinner" /><span>Loading track data...</span></div>
      ) : trackError ? (
        <div className="error-box">⚠️ Map error: {trackError}</div>
      ) : (
        <CycloneMap track={track} />
      )}

      {/* Intensity chart */}
      {chartData.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <p style={{ fontWeight: 700, marginBottom: 8 }}>Cyclone Intensity Over Time</p>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A4A6A" />
              <XAxis dataKey="time" stroke="#90A4AE" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="wind" orientation="left" stroke="#FF6D00"
                     label={{ value: "Wind (km/h)", angle: -90, position: "insideLeft", fill: "#FF6D00", fontSize: 11 }} />
              <YAxis yAxisId="pressure" orientation="right" stroke="#00B0FF"
                     domain={["auto", "auto"]}
                     label={{ value: "Pressure (hPa)", angle: 90, position: "insideRight", fill: "#00B0FF", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#1E2A3A", border: "1px solid #2A4A6A", color: "#E8F4F8" }}
                       formatter={(val: number, name: string) => [
                         `${val}${name === "wind" ? " km/h" : " hPa"}`, name === "wind" ? "Wind" : "Pressure"
                       ]} />
              <Legend />
              <Line yAxisId="wind" type="monotone" dataKey="wind" stroke="#FF6D00" strokeWidth={2}
                    dot={{ r: 3, fill: "#FF6D00" }} name="Wind Speed" />
              <Line yAxisId="pressure" type="monotone" dataKey="pressure" stroke="#00B0FF" strokeWidth={2}
                    dot={{ r: 3, fill: "#00B0FF" }} strokeDasharray="4 2" name="Pressure" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Track data table */}
      {track.length > 0 && (
        <details style={{ marginTop: 16 }}>
          <summary style={{ cursor: "pointer", color: "#64B5F6", fontWeight: 600 }}>📋 Track Data Table</summary>
          <div style={{ overflowX: "auto", marginTop: 8 }}>
            <table>
              <thead>
                <tr>
                  <th>Time</th><th>Lat</th><th>Lon</th><th>Intensity</th>
                  <th>Wind (km/h)</th><th>Pressure (hPa)</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {track.map((p, i) => (
                  <tr key={i}>
                    <td>{p.timestamp.slice(0, 16).replace("T", " ")}</td>
                    <td>{p.latitude}</td><td>{p.longitude}</td>
                    <td>
                      <span style={{
                        background: `${INTENSITY_COLORS[p.intensity_category] ?? "#607D8B"}44`,
                        color: INTENSITY_COLORS[p.intensity_category] ?? "#E8F4F8",
                        padding: "2px 8px", borderRadius: 4, fontSize: "0.82em",
                      }}>{p.intensity_category}</span>
                    </td>
                    <td>{p.wind_speed_kmh}</td><td>{p.pressure_hpa}</td>
                    <td>{p.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      {latest && (
        <p style={{ marginTop: 12, fontSize: "0.8em", color: "#7A9BB5" }}>
          ⚠️ Data source: {latest.source} — Not a real-time official cyclone track
        </p>
      )}
    </div>
  );
}
