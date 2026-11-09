"use client";
import type { AnalysisSession, WeatherReading } from "../../lib/api";
import { useEffect, useState } from "react";
import { fetchWeather } from "../../lib/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ResponsiveContainer, ReferenceLine,
} from "recharts";

interface Props { session: AnalysisSession | null; }

export default function WeatherPage({ session }: Props) {
  const [weatherData, setWeatherData] = useState<WeatherReading[]>([]);
  const [loadingCharts, setLoadingCharts] = useState(false);

  useEffect(() => {
    setLoadingCharts(true);
    fetchWeather(false)
      .then((r) => setWeatherData(r.readings))
      .catch(() => {/* non-critical */})
      .finally(() => setLoadingCharts(false));
  }, []);

  if (!session) {
    return (
      <div>
        <div className="section-header">🌦️ Weather Intelligence</div>
        <div className="info-box">Run the analysis first (click '🚀 Run Analysis' in the sidebar).</div>
      </div>
    );
  }

  const out = (session.weather_result?.output ?? {}) as Record<string, unknown>;
  if (!out || Object.keys(out).length === 0) {
    return (
      <div>
        <div className="section-header">🌦️ Weather Intelligence</div>
        <div className="error-box">Weather agent produced no output.</div>
      </div>
    );
  }

  const stats = (out._stats ?? {}) as Record<string, unknown>;
  const anomalies = (out.anomalies_detected as string[]) ?? [];
  const recommendation = out.recommendation as string;
  const confidence = (out.confidence as number) ?? 0;

  // Prepare chart data — group by station name across timestamps
  const pressureChartData: Record<string, unknown>[] = [];
  const windChartData: { station: string; wind: number }[] = [];
  const latestByStation: Record<string, WeatherReading> = {};

  for (const r of weatherData) {
    if (r.station_name) latestByStation[r.station_name] = r;
    if (r.timestamp && r.pressure_hpa != null) {
      const existing = pressureChartData.find((d) => d.time === r.timestamp);
      if (existing) {
        (existing as Record<string, unknown>)[r.station_name] = r.pressure_hpa;
      } else {
        pressureChartData.push({ time: r.timestamp.slice(11, 16), [r.station_name]: r.pressure_hpa });
      }
    }
  }
  for (const [name, r] of Object.entries(latestByStation)) {
    if (r.wind_speed_kmh != null) windChartData.push({ station: name, wind: r.wind_speed_kmh });
  }
  const CHART_COLORS = ["#64B5F6", "#FF6D00", "#00BFA5", "#9C27B0", "#FFC400", "#00C853"];
  const stationNames = [...new Set(weatherData.map((r) => r.station_name))];

  return (
    <div>
      <div className="section-header">🌦️ Weather Intelligence</div>
      {(session.provider_name === "demo" || session.data_mode === "sample") && (
        <div className="demo-banner">
          ⚠️ <strong>DEMO / SAMPLE DATA</strong> — These readings are synthetic test data.
          They are <strong>not</strong> real weather observations.
        </div>
      )}

      {/* Stats */}
      <div className="card-grid">
        {[
          { label: "Min Pressure", value: stats.pressure_min_hpa != null ? `${stats.pressure_min_hpa} hPa` : "?" },
          { label: "Max Wind", value: stats.wind_max_kmh != null ? `${stats.wind_max_kmh} km/h` : "?" },
          { label: "Avg Humidity", value: stats.humidity_avg_pct != null ? `${stats.humidity_avg_pct}%` : "?" },
          { label: "Total Rainfall", value: stats.rainfall_total_mm != null ? `${stats.rainfall_total_mm} mm` : "?" },
          { label: "Stations", value: String(stats.station_count ?? "?") },
          { label: "Data Quality", value: (out.data_quality as string)?.toUpperCase() ?? "?" },
        ].map((m) => (
          <div key={m.label} className="metric-card">
            <div className="metric-label">{m.label}</div>
            <div className="metric-value" style={{ fontSize: "1.2em" }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div>
          <div className="section-header">Analysis Summary</div>
          <div className="card">
            <p style={{ marginBottom: 8 }}>{out.analysis_summary as string}</p>
            <p><strong>Pressure Trend:</strong> {out.pressure_trend as string}</p>
            <p><strong>Wind Assessment:</strong> {out.wind_assessment as string}</p>
            <p><strong>Humidity:</strong> {out.humidity_level as string}</p>
          </div>
        </div>
        <div>
          <div className="section-header">Anomalies &amp; Recommendation</div>
          <div className="card">
            {anomalies.length > 0 ? anomalies.map((a, i) => (
              <div key={i} className="alert-banner" style={{ borderColor: "#FFC400", background: "#FFC40011", marginBottom: 6 }}>
                ⚠️ {a}
              </div>
            )) : <p style={{ color: "#00C853" }}>✅ No anomalies detected</p>}
            <div style={{ marginTop: 12 }}>
              <strong>Recommendation: </strong>
              <span style={{ color: recommendation?.includes("Escalate") ? "#FF5252" : "#00C853" }}>
                {recommendation?.includes("Escalate") ? "🔴" : "🟢"} {recommendation}
              </span>
            </div>
            <div style={{ marginTop: 8, color: "#90A4AE" }}>Confidence: {(confidence * 100).toFixed(0)}%</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      {!loadingCharts && weatherData.length > 0 && (
        <div className="grid-2">
          <div className="card">
            <p style={{ fontWeight: 700, marginBottom: 8 }}>Atmospheric Pressure Trend (hPa)</p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={pressureChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A4A6A" />
                <XAxis dataKey="time" stroke="#90A4AE" tick={{ fontSize: 11 }} />
                <YAxis domain={["auto", "auto"]} stroke="#90A4AE" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#1E2A3A", border: "1px solid #2A4A6A", color: "#E8F4F8" }} />
                <Legend />
                <ReferenceLine y={990} stroke="#FF6D00" strokeDasharray="4 2" label={{ value: "990", fill: "#FF6D00", fontSize: 11 }} />
                <ReferenceLine y={980} stroke="#FF1744" strokeDasharray="4 2" label={{ value: "980", fill: "#FF1744", fontSize: 11 }} />
                {stationNames.map((name, i) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={CHART_COLORS[i % CHART_COLORS.length]}
                        strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <p style={{ fontWeight: 700, marginBottom: 8 }}>Wind Speed by Station (km/h)</p>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={windChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A4A6A" />
                <XAxis dataKey="station" stroke="#90A4AE" tick={{ fontSize: 10 }} />
                <YAxis stroke="#90A4AE" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#1E2A3A", border: "1px solid #2A4A6A", color: "#E8F4F8" }} />
                <ReferenceLine y={63} stroke="#FFC400" strokeDasharray="4 2" label={{ value: "63 km/h", fill: "#FFC400", fontSize: 10 }} />
                <ReferenceLine y={89} stroke="#FF6D00" strokeDasharray="4 2" label={{ value: "89 km/h", fill: "#FF6D00", fontSize: 10 }} />
                <Bar dataKey="wind" fill="#64B5F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Raw JSON */}
      <details style={{ marginTop: 16 }}>
        <summary style={{ cursor: "pointer", color: "#64B5F6", fontWeight: 600 }}>Raw Weather Agent JSON</summary>
        <pre style={{ marginTop: 8 }}>{JSON.stringify(out, null, 2)}</pre>
      </details>
    </div>
  );
}
