"use client";

/**
 * Signals Page
 * 
 * Main page for viewing emerging signals detected from KG snapshot comparisons.
 * Displays the SignalDashboard component with filtering and sorting options.
 */

import { SignalDashboard } from "@/components/SignalDashboard";

export default function SignalsPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f8fafc",
        padding: "2rem",
      }}
    >
      <div
        style={{
          maxWidth: "1400px",
          margin: "0 auto",
        }}
      >
        <SignalDashboard />
      </div>
    </div>
  );
}
