"use client";

import * as Popover from "@radix-ui/react-popover";
import { ChevronDown, Command, PauseOctagon, Play, Search, UserCog } from "lucide-react";
import { useMissions } from "@/lib/hooks";
import { ROLE_LABEL, USERS, useRole } from "@/lib/role";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge, IconButton, Tooltip } from "@/components/forge/primitives";
import { SyntheticBadge } from "./synthetic-badge";
import { useShell } from "./shell-context";

const ROLES: Role[] = ["supervisor", "technician", "quality_engineer", "plant_admin"];

export function CommandBar() {
  const { role, setRole } = useRole();
  const { data } = useMissions();
  const { setCommandOpen, agentPaused, setAgentPaused } = useShell();
  const activeCount = data?.missions.filter((m) => m.is_active).length ?? 0;

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-raised/80 px-4 backdrop-blur">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold text-ink-hi">Northstar Packaging Plant</span>
        <span className="text-ink-faint">·</span>
        <span className="mono text-xs text-ink-mut">Shift B</span>
      </div>

      <div className="ml-2 hidden items-center gap-2 md:flex">
        <Badge tone="agent" dot>{activeCount} active mission{activeCount === 1 ? "" : "s"}</Badge>
        <Badge tone="verified" dot>Agent online</Badge>
      </div>

      <button
        onClick={() => setCommandOpen(true)}
        className="group ml-auto flex h-9 w-64 items-center gap-2 rounded-[10px] border border-line bg-surface-1 px-3 text-sm text-ink-mut hover:border-line-strong"
        aria-label="Open command palette"
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left text-xs">Search or run command</span>
        <kbd className="mono flex items-center gap-0.5 rounded border border-line bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-mut">
          <Command className="h-3 w-3" />K
        </kbd>
      </button>

      <Tooltip content={agentPaused ? "Resume agent side effects" : "Emergency pause — block all agent side effects"}>
        <button
          onClick={() => setAgentPaused(!agentPaused)}
          aria-pressed={agentPaused}
          className={cn(
            "inline-flex h-9 items-center gap-1.5 rounded-[10px] border px-2.5 text-xs font-medium transition-colors",
            agentPaused
              ? "border-failure/50 bg-failure-soft text-failure"
              : "border-line text-ink-mut hover:text-ink hover:bg-surface-2",
          )}
        >
          {agentPaused ? <Play className="h-3.5 w-3.5" /> : <PauseOctagon className="h-3.5 w-3.5" />}
          {agentPaused ? "Paused" : "Pause"}
        </button>
      </Tooltip>

      {/* role switcher */}
      <Popover.Root>
        <Popover.Trigger asChild>
          <button className="inline-flex h-9 items-center gap-2 rounded-[10px] border border-line bg-surface-1 px-2.5 text-xs hover:border-line-strong" aria-label="Switch role">
            <span className="grid h-6 w-6 place-items-center rounded-md bg-approval-soft text-approval">
              <UserCog className="h-3.5 w-3.5" />
            </span>
            <span className="text-ink">{ROLE_LABEL[role]}</span>
            <ChevronDown className="h-3.5 w-3.5 text-ink-mut" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content sideOffset={6} align="end" className="z-50 w-60 rounded-lg border border-line-strong bg-surface-3 p-1.5 shadow-e3 animate-fade-up">
            <div className="px-2 py-1.5 text-[11px] text-ink-mut">View the workspace as a role. Backend authorization stays authoritative.</div>
            {ROLES.map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={cn(
                  "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-2",
                  r === role ? "text-agent" : "text-ink",
                )}
              >
                <span>{ROLE_LABEL[r]}</span>
                <span className="mono text-[11px] text-ink-mut">{USERS[r].username}</span>
              </button>
            ))}
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>

      <div className="hidden lg:block">
        <SyntheticBadge compact />
      </div>
    </header>
  );
}
