"use client";

/** Root error boundary — the last-resort net if the root layout itself throws. It must render its own
 * <html>/<body> because it replaces the root layout. Kept dependency-free and inline-styled so it works
 * even if the stylesheet/layout is what failed. */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ background: "#0a0c10", color: "#e6e8ee", fontFamily: "system-ui, sans-serif", margin: 0 }}>
        <div style={{ display: "grid", placeItems: "center", minHeight: "100vh", padding: 24 }}>
          <div style={{ maxWidth: 420, textAlign: "center", border: "1px solid #3a1d1d", background: "#1a0f10", borderRadius: 12, padding: 24 }}>
            <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>Recovery Agent failed to load</h2>
            <p style={{ margin: "0 0 16px", fontSize: 14, color: "#9aa0ad" }}>
              The application hit an unexpected error. No recovery data was changed on the server.
            </p>
            <button
              onClick={() => reset()}
              style={{ background: "#4c7dff", color: "#000", border: 0, borderRadius: 8, padding: "8px 14px", fontSize: 14, cursor: "pointer" }}
            >
              Reload
            </button>
            {error?.digest && <p style={{ marginTop: 12, fontSize: 11, color: "#5c6270" }}>ref: {error.digest}</p>}
          </div>
        </div>
      </body>
    </html>
  );
}
