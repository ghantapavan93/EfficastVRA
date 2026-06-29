"use client";

import { AlertTriangle, Inbox, Lock, RefreshCw, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./primitives";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-lg", className)} aria-hidden />;
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-mut" role="status" aria-live="polite">
      <div className="flex gap-1.5" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 rounded-full bg-agent animate-pulse-soft"
            style={{ animationDelay: `${i * 0.18}s` }}
          />
        ))}
      </div>
      <span className="text-sm">{label}…</span>
    </div>
  );
}

/** Generative "awaiting signal" illustration — a telemetry baseline with a soft scanning sweep, with the
 *  contextual icon set in a node. Makes data-less screens look intentional rather than blank. */
function EmptyArt({ Icon }: { Icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="relative mb-1 h-16 w-44" aria-hidden>
      <svg viewBox="0 0 180 70" className="h-full w-full">
        <style>{`@keyframes es-sweep{0%{transform:translateX(0);opacity:0}15%,85%{opacity:.55}100%{transform:translateX(162px);opacity:0}}@media (prefers-reduced-motion:reduce){.es-sweep{animation:none!important}}`}</style>
        {[18, 34, 50].map((y) => (
          <line key={y} x1="9" y1={y} x2="171" y2={y} stroke="var(--line)" strokeWidth="0.6" strokeDasharray="2 6" opacity="0.5" />
        ))}
        <line x1="9" y1="50" x2="171" y2="50" stroke="var(--line-strong)" strokeWidth="1" />
        <path d="M9,50 Q42,48 66,49 T122,48 T171,49" fill="none" stroke="var(--agent)" strokeWidth="1.6" opacity="0.5" />
        <rect className="es-sweep" x="9" y="12" width="1.4" height="44" fill="var(--agent)" opacity="0.5" style={{ animation: "es-sweep 4s linear infinite" }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <span className="grid h-9 w-9 place-items-center rounded-full border border-line bg-surface-2 shadow-[0_0_18px_-8px_var(--agent)]">
          <Icon className="h-4 w-4 text-ink-mut" />
        </span>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
}: {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line py-14 text-center">
      <EmptyArt Icon={Icon} />
      <div className="text-sm font-medium text-ink">{title}</div>
      {description && <div className="max-w-sm text-xs text-ink-mut">{description}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-failure/30 bg-failure-soft py-12 text-center"
      role="alert"
    >
      <AlertTriangle className="h-7 w-7 text-failure" />
      <div className="text-sm text-ink">{message}</div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </Button>
      )}
    </div>
  );
}

export function OfflineState() {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-warning" role="status">
      <WifiOff className="h-4 w-4" /> Backend unreachable — showing last known state.
    </div>
  );
}

export function PermissionDeniedState({ reason }: { reason: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-ink-mut" role="status">
      <Lock className="h-4 w-4 text-ink-faint" /> {reason}
    </div>
  );
}
