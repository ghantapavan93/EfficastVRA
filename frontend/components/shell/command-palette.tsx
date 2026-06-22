"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Command } from "cmdk";
import {
  Activity,
  FileCheck2,
  Gauge,
  ListChecks,
  PauseOctagon,
  Play,
  RotateCcw,
  ScrollText,
  Trophy,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useMissions } from "@/lib/hooks";
import { useShell } from "./shell-context";

export function CommandPalette() {
  const { commandOpen, setCommandOpen, agentPaused, setAgentPaused } = useShell();
  const { data } = useMissions();
  const router = useRouter();
  const qc = useQueryClient();
  const primary = data?.missions.find((m) => m.is_active)?.id ?? data?.missions[0]?.id;

  const go = (href: string) => {
    setCommandOpen(false);
    router.push(href);
  };
  const run = async (fn: () => Promise<unknown>) => {
    setCommandOpen(false);
    await fn();
    qc.invalidateQueries();
  };

  return (
    <Command.Dialog
      open={commandOpen}
      onOpenChange={setCommandOpen}
      label="Command palette"
      className="fixed left-1/2 top-[18%] z-[60] w-[min(92vw,560px)] -translate-x-1/2 overflow-hidden rounded-xl border border-line-strong bg-surface-3 shadow-e3"
      overlayClassName="fixed inset-0 z-[59] bg-[var(--scrim)] backdrop-blur-sm"
    >
      <div className="flex items-center gap-2 border-b border-line px-3">
        <Zap className="h-4 w-4 text-agent" />
        <Command.Input
          placeholder="Search or run a command…"
          className="h-12 flex-1 bg-transparent text-sm text-ink-hi outline-none placeholder:text-ink-faint"
        />
      </div>
      <Command.List className="max-h-[360px] overflow-y-auto p-1.5">
        <Command.Empty className="px-3 py-6 text-center text-sm text-ink-mut">No matching commands.</Command.Empty>

        <Command.Group heading="Navigate" className="px-1 py-1 text-[11px] text-ink-mut [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1">
          <Item icon={Gauge} onSelect={() => go("/missions")}>Open Mission Control</Item>
          {primary && <Item icon={Activity} onSelect={() => go(`/missions/${primary}`)}>Open active recovery mission</Item>}
          {primary && <Item icon={FileCheck2} onSelect={() => go(`/missions/${primary}?tab=contract`)}>View Recovery Contract</Item>}
          {primary && <Item icon={ListChecks} onSelect={() => go(`/missions/${primary}?tab=evidence`)}>View missing evidence</Item>}
          {primary && <Item icon={ScrollText} onSelect={() => go(`/missions/${primary}?tab=timeline`)}>Open verification timeline & audit</Item>}
          {primary && <Item icon={Trophy} onSelect={() => go(`/missions/${primary}?tab=outcome`)}>View outcome & knowledge candidate</Item>}
        </Command.Group>

        <Command.Group heading="Agent" className="px-1 py-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:text-ink-mut">
          <Item icon={agentPaused ? Play : PauseOctagon} onSelect={() => { setAgentPaused(!agentPaused); setCommandOpen(false); }}>
            {agentPaused ? "Resume agent side effects" : "Pause agent side effects"}
          </Item>
        </Command.Group>

        <Command.Group heading="Demo (synthetic)" className="px-1 py-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:text-ink-mut">
          <Item icon={RotateCcw} onSelect={() => run(api.demoReset)}>Reset synthetic plant</Item>
          <Item icon={Play} onSelect={() => run(api.demoRun)}>Replay full scenario (headless)</Item>
        </Command.Group>
      </Command.List>
      <div className="border-t border-line px-3 py-2 text-[11px] text-ink-faint">
        Machine-control commands are never available — this agent cannot operate equipment.
      </div>
    </Command.Dialog>
  );
}

function Item({
  children,
  icon: Icon,
  onSelect,
}: {
  children: React.ReactNode;
  icon: React.ComponentType<{ className?: string }>;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-sm text-ink aria-selected:bg-surface-1 aria-selected:text-ink-hi"
    >
      <Icon className="h-4 w-4 text-ink-mut" />
      {children}
    </Command.Item>
  );
}
