"use client";

import { useEffect, useRef, useState } from "react";

/** Animate a number from its previous value to `target` (easeOutCubic via rAF). Respects reduced-motion. */
export function useCountUp(target: number, duration = 850): number {
  const [val, setVal] = useState(target);
  const fromRef = useRef(target);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const from = fromRef.current;
    const to = target;
    if (reduce || from === to || !Number.isFinite(to)) {
      setVal(to);
      fromRef.current = to;
      return;
    }
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(from + (to - from) * eased);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        fromRef.current = to;
      }
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return val;
}

export function CountUp({
  value,
  decimals = 0,
  prefix = "",
  suffix = "",
  signed = false,
  className,
}: {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  signed?: boolean;
  className?: string;
}) {
  const v = useCountUp(value);
  const sign = signed && v >= 0 ? "+" : "";
  return <span className={className}>{prefix}{sign}{v.toFixed(decimals)}{suffix}</span>;
}
