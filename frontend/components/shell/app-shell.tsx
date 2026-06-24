"use client";

import { PlayCircle } from "lucide-react";
import { useMe } from "@/lib/hooks";
import { CommandBar } from "./command-bar";
import { CommandPalette } from "./command-palette";
import { NavRail } from "./nav-rail";
import { ShellProvider, useShell } from "./shell-context";
import { StatusStrip } from "./status-strip";
import { DemoController } from "@/components/demo/demo-controller";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ShellProvider>
      <ShellInner>{children}</ShellInner>
    </ShellProvider>
  );
}

function ShellInner({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-canvas flex h-screen overflow-hidden">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[100] focus:rounded-md focus:bg-surface-3 focus:px-3 focus:py-2 focus:text-sm">
        Skip to content
      </a>
      <NavRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <CommandBar />
        <main id="main" className="grid-motif flex-1 overflow-y-auto">
          {children}
        </main>
        <StatusStrip />
      </div>
      <CommandPalette />
      <DemoController />
      <DemoToggle />
      <div id="vra-live" aria-live="polite" className="sr-only" />
    </div>
  );
}

function DemoToggle() {
  const { data: me } = useMe();
  const { demoOpen, setDemoOpen } = useShell();
  if (!me?.demo_mode || demoOpen) return null;
  return (
    <button
      onClick={() => setDemoOpen(true)}
      className="fixed bottom-5 right-5 z-30 inline-flex items-center gap-2 rounded-pill border border-brand/40 bg-brand-soft px-4 py-2.5 text-sm font-semibold text-brand shadow-e2 transition-transform hover:scale-[1.02]"
      aria-label="Open demo controller"
    >
      <PlayCircle className="h-4 w-4" /> Demo
    </button>
  );
}
