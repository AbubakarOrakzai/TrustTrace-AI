import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustTrace AI | Agent Firewall",
  description: "Local-first AI agent tool-call security and audit dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
