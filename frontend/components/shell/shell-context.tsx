"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

interface ShellCtx {
  agentPaused: boolean;
  setAgentPaused: (v: boolean) => void;
  commandOpen: boolean;
  setCommandOpen: (v: boolean) => void;
  demoOpen: boolean;
  setDemoOpen: (v: boolean) => void;
}

const Ctx = createContext<ShellCtx | null>(null);

export function ShellProvider({ children }: { children: React.ReactNode }) {
  const [agentPaused, setAgentPaused] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);

  const onKey = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      setCommandOpen((v) => !v);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  return (
    <Ctx.Provider value={{ agentPaused, setAgentPaused, commandOpen, setCommandOpen, demoOpen, setDemoOpen }}>
      {children}
    </Ctx.Provider>
  );
}

export function useShell(): ShellCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useShell must be used within ShellProvider");
  return c;
}
