"use client";

import { useEffect, useState } from "react";
import { useMissions } from "@/lib/hooks";
import { Badge } from "@/components/forge/primitives";

/**
 * Live connection/freshness indicator (gap M7). The UI polls, so a dropped backend would otherwise serve
 * the last cache indefinitely with confident, frozen numbers. This reflects the *real* state: Live when
 * data is fresh, Stale when it's aged or erroring, Offline when the browser has no network — so a viewer
 * never mistakes a frozen screen for a live one.
 */
export function ConnectionStatus() {
  const { dataUpdatedAt, isError } = useMissions(8000);
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const sync = () => setOnline(navigator.onLine);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  if (!online) return <Badge tone="failure" dot>Offline · last known</Badge>;

  const ageS = dataUpdatedAt ? Math.round((Date.now() - dataUpdatedAt) / 1000) : null;
  if (isError || (ageS != null && ageS > 25)) {
    return <Badge tone="warning" dot>Stale{ageS != null ? ` · ${ageS}s` : ""}</Badge>;
  }
  return (
    <span title={ageS != null ? `Updated ${ageS}s ago` : "Live"}>
      <Badge tone="verified" dot>Live</Badge>
    </span>
  );
}
