"use client";
/**
 * Leaflet map component — only rendered on client side (no SSR).
 * Shows cyclone track with color-coded intensity markers.
 */
import type { TrackPoint } from "../../lib/api";
import { useEffect, useRef } from "react";

interface Props { track: TrackPoint[]; }

const INTENSITY_COLORS: Record<string, string> = {
  "Depression": "#AED6F1",
  "Deep Depression": "#85C1E9",
  "Cyclonic Storm": "#F1C40F",
  "Severe Cyclonic Storm": "#E67E22",
  "Very Severe Cyclonic Storm": "#E74C3C",
  "Extremely Severe Cyclonic Storm": "#922B21",
  "Super Cyclonic Storm": "#6C0000",
};

const COASTAL_CITIES = [
  { name: "Puri", lat: 19.80, lon: 85.83 },
  { name: "Gopalpur", lat: 19.27, lon: 84.90 },
  { name: "Visakhapatnam", lat: 17.68, lon: 83.22 },
  { name: "Chennai", lat: 13.08, lon: 80.27 },
  { name: "Bhubaneswar", lat: 20.29, lon: 85.82 },
  { name: "Kolkata", lat: 22.57, lon: 88.36 },
];

export default function CycloneMap({ track }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const leafletMap = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current) return;
    // Dynamically import leaflet to avoid SSR issues
    import("leaflet").then((L) => {
      // Delete default icon urls that break in Next.js
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      if (leafletMap.current) {
        leafletMap.current.remove();
      }
      const map = L.map(mapRef.current!, { center: [15, 82], zoom: 5 });
      leafletMap.current = map;

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      if (track.length > 0) {
        // Track polyline
        const coords: [number, number][] = track
          .filter((p) => p.latitude != null && p.longitude != null)
          .map((p) => [p.latitude, p.longitude]);
        L.polyline(coords, { color: "#FF6D00", weight: 3, opacity: 0.9 })
          .addTo(map)
          .bindTooltip("Cyclone Track");

        // Track markers
        track.forEach((point, i) => {
          if (point.latitude == null || point.longitude == null) return;
          const color = INTENSITY_COLORS[point.intensity_category] ?? "#90A4AE";
          const radius = i === track.length - 1 ? 12 : 6;
          const circle = L.circleMarker([point.latitude, point.longitude], {
            radius, color, fillColor: color, fillOpacity: 0.85, weight: 1,
          });
          circle.bindPopup(
            `<b>${point.storm_name}</b><br>` +
            `Time: ${point.timestamp.slice(0, 16).replace("T", " ")}<br>` +
            `Intensity: ${point.intensity_category}<br>` +
            `Wind: ${point.wind_speed_kmh} km/h<br>` +
            `Pressure: ${point.pressure_hpa} hPa`
          );
          circle.bindTooltip(`${point.intensity_category} — ${point.timestamp.slice(0, 10)}`);
          circle.addTo(map);
        });

        // Fit map to track
        map.fitBounds(L.latLngBounds(coords), { padding: [40, 40] });
      }

      // Coastal city markers
      COASTAL_CITIES.forEach(({ name, lat, lon }) => {
        L.marker([lat, lon])
          .addTo(map)
          .bindTooltip(name);
      });
    }).catch(() => {
      // Leaflet import failure handled by container error state
    });

    return () => {
      if (leafletMap.current) {
        leafletMap.current.remove();
        leafletMap.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [track]);

  return (
    <>
      {/* Leaflet CSS */}
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossOrigin=""
      />
      <div
        ref={mapRef}
        style={{ width: "100%", height: 480, borderRadius: 8, border: "1px solid #2A4A6A" }}
      />
    </>
  );
}
