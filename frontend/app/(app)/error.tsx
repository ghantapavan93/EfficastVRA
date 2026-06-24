"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

/** App-segment error boundary — catches **synchronous render errors** (e.g. a component dereferencing a
 * malformed/partial payload) and shows a clear retry instead of a white screen. NOTE: by React's design
 * it does NOT catch errors thrown in event handlers or async callbacks, and query errors are surfaced as
 * each panel's inline ErrorState (TanStack `isError`), not thrown here — so this is the last-resort net
 * for render throws, not a catch-all. The backend remains the source of truth. */
export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Surface to the console for diagnostics (a real deployment would ship this to an error tracker).
    console.error("Recovery Agent UI error:", error);
  }, [error]);

  return (
    <div role="alert" className="grid min-h-[60vh] place-items-center p-6">
      <div className="max-w-md rounded-xl border border-failure/40 bg-failure-soft p-6 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-failure" aria-hidden />
        <h2 className="mt-3 text-lg font-semibold text-ink-hi">Something went wrong</h2>
        <p className="mt-1 text-sm text-ink-mut">
          This view couldn&apos;t render. Your recovery data is safe on the server — nothing was changed.
          Retry, or switch to another view.
        </p>
        <button
          onClick={() => reset()}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-agent px-3 py-2 text-sm font-medium text-black transition-opacity hover:opacity-90"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Retry
        </button>
        {error?.digest && <p className="mt-3 mono text-[11px] text-ink-faint">ref: {error.digest}</p>}
      </div>
    </div>
  );
}
