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
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line py-16 text-center">
      <Icon className="h-7 w-7 text-ink-faint" />
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
