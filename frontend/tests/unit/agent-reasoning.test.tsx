import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ReasoningView } from "@/lib/types";

const fixture: ReasoningView = {
  incident_id: "INC-2841",
  provider: "DeterministicReasoningProvider",
  prompt_version: "deterministic-1",
  confidence: 0.97,
  step_count: 4,
  note: "The model proposes and explains; a deterministic evaluator judges recovery.",
  steps: [
    {
      seq: 2, node: "retrieve", node_label: "Retrieve",
      title: "Retrieved 4 approved sources; suppressed 6 non-authoritative",
      rationale: "Filters by applicability and approval before similarity.",
      inputs: { query: "recovery requirements" },
      outputs: { suppressed: [{ document_id: "DOC-NOTE", approval_status: "UNAPPROVED" }] },
      citations: [{ document_id: "DOC-CDX", section: "4.2", approval_status: "APPROVED", excerpt: "vibration ≤ 4.0" }],
      confidence: null, revision: 0, contract_id: "RC-1042", model_version: "DeterministicReasoningProvider",
      prompt_version: "deterministic-1", at: null,
    },
    {
      seq: 8, node: "reflect", node_label: "Reflect",
      title: "Recovery Contract RC-1042 v1 violated — fault F27 recurred",
      rationale: "A completed work order is not proof of recovery.",
      inputs: { cycle: 17 }, outputs: { verdict: "violated" }, citations: [],
      confidence: 0.05, revision: 0, contract_id: "RC-1042", model_version: "DeterministicReasoningProvider",
      prompt_version: "deterministic-1", at: null,
    },
    {
      seq: 10, node: "decide", node_label: "Decide",
      title: "Recovery verified — closure justified",
      rationale: "30/30 stable cycles, every condition passed, quality released.",
      inputs: {}, outputs: { verdict: "verified" }, citations: [],
      confidence: 0.97, revision: 0, contract_id: "RC-1042", model_version: "DeterministicReasoningProvider",
      prompt_version: "deterministic-1", at: null,
    },
  ],
};

vi.mock("@/lib/hooks", () => ({
  useReasoning: () => ({ data: fixture, isLoading: false, isError: false, refetch: () => {} }),
}));

import { AgentReasoning } from "@/components/mission/agent-reasoning";

describe("AgentReasoning", () => {
  it("renders the provider, step count and overall recovery confidence", () => {
    render(<AgentReasoning incidentId="INC-2841" />);
    expect(screen.getByText("DeterministicReasoningProvider")).toBeInTheDocument();
    expect(screen.getByText(/recovery confidence 97%/)).toBeInTheDocument();
  });

  it("shows the cycle-17 violation reflection and the verified decision", () => {
    render(<AgentReasoning incidentId="INC-2841" />);
    expect(screen.getByText(/violated — fault F27 recurred/)).toBeInTheDocument();
    expect(screen.getByText(/Recovery verified — closure justified/)).toBeInTheDocument();
  });

  it("surfaces the retrieval guardrail (non-authoritative sources suppressed)", () => {
    render(<AgentReasoning incidentId="INC-2841" />);
    expect(screen.getByText(/suppressed 6 non-authoritative/)).toBeInTheDocument();
  });

  it("states that the agent proposes but never decides or acts on its own", () => {
    render(<AgentReasoning incidentId="INC-2841" />);
    expect(screen.getByText(/never decides or acts on its own/)).toBeInTheDocument();
  });
});
