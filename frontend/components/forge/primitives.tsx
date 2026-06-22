"use client";

import * as RadixTooltip from "@radix-ui/react-tooltip";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { TONE_CLASS, type Tone } from "@/lib/state-meta";

// ── Button ───────────────────────────────────────────────────────────────────
type Variant = "primary" | "agent" | "outline" | "ghost" | "danger" | "approval";
const VARIANT: Record<Variant, string> = {
  primary: "bg-brand text-black hover:bg-brand/90 active:bg-brand-press font-semibold",
  agent: "bg-agent text-white hover:bg-agent/90 font-semibold",
  approval: "bg-approval text-white hover:bg-approval/90 font-semibold",
  danger: "bg-failure/90 text-white hover:bg-failure font-semibold",
  outline: "border border-line-strong text-ink hover:border-ink-mut hover:bg-surface-2",
  ghost: "text-ink-mut hover:text-ink hover:bg-surface-2",
};

export const Button = forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" }
>(({ className, variant = "outline", size = "md", ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center gap-2 rounded-[10px] transition-all duration-150",
      "disabled:opacity-40 disabled:pointer-events-none active:scale-[.98] whitespace-nowrap",
      size === "sm" ? "h-8 px-3 text-[13px]" : "h-10 px-4 text-sm",
      VARIANT[variant],
      className,
    )}
    {...props}
  />
));
Button.displayName = "Button";

export function IconButton({
  className,
  label,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      aria-label={label}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-[10px] text-ink-mut",
        "hover:text-ink hover:bg-surface-2 transition-colors duration-150",
        className,
      )}
      {...props}
    />
  );
}

// ── Badge / Chip ───────────────────────────────────────────────────────────────
export function Badge({
  tone = "steel",
  children,
  dot = false,
  className,
}: {
  tone?: Tone;
  children: React.ReactNode;
  dot?: boolean;
  className?: string;
}) {
  const t = TONE_CLASS[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-0.5 text-[11px] font-medium",
        t.text,
        t.bg,
        t.border,
        className,
      )}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full", t.dot)} aria-hidden />}
      {children}
    </span>
  );
}

export function Chip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "mono inline-flex items-center gap-1 rounded-md border border-line bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-mut",
        className,
      )}
    >
      {children}
    </span>
  );
}

// ── Tooltip ────────────────────────────────────────────────────────────────────
export function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactNode }) {
  return (
    <RadixTooltip.Provider delayDuration={200}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            sideOffset={6}
            className="z-50 max-w-xs rounded-lg border border-line-strong bg-surface-3 px-3 py-2 text-xs text-ink shadow-e3 animate-fade-up"
          >
            {content}
            <RadixTooltip.Arrow className="fill-[var(--surface-3)]" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}

// ── Misc ─────────────────────────────────────────────────────────────────────
export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("label", className)}>{children}</div>;
}

export function ProgressBar({ value, tone = "agent" }: { value: number; tone?: Tone }) {
  const t = TONE_CLASS[tone];
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-pill bg-surface-3">
      <div
        className={cn("h-full rounded-pill transition-[width] duration-500 ease-out", t.dot)}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function MetricValue({
  value,
  unit,
  className,
}: {
  value: React.ReactNode;
  unit?: string;
  className?: string;
}) {
  return (
    <span className={cn("mono text-ink-hi", className)}>
      {value}
      {unit && <span className="ml-0.5 text-[0.7em] text-ink-mut">{unit}</span>}
    </span>
  );
}
