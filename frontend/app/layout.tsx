import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CycloneShield AI — Cyclone Detection & Early Warning",
  description:
    "Agentic AI-based cyclone detection and early warning system for coastal India. Powered by IBM watsonx.ai Granite.",
  keywords: "cyclone, early warning, India, AI, weather, IMD",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
