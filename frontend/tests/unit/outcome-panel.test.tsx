import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { OutcomeView } from "@/lib/types";

// A *partial* 200 (before/after omitted) — this used to crash the before/after table with a
// TypeError. The panel must now degrade those cells to "—" instead of throwing.
const partial: OutcomeView = {
  incident_id: "INC-2841", state: "MONITORING_RECOVERY", outcome_type: null,
  summary: "In progress.", stable_cycles: 12, required_stable_cycles: 30, reopened_count: 1,
  interventions: [], lots: [], quality_released: false, policy_version: null,
  knowledge_candidate: null, closed_at: null,
};

vi.mock("@/lib/hooks", () => ({
  useOutcome: () => ({ data: partial, isLoading: false, isError: false, refetch: () => {} }),
}));

import { OutcomePanel } from "@/components/outcome/outcome-panel";

describe("OutcomePanel", () => {
  it("renders partial outcome data (missing before/after) without crashing", () => {
    render(<OutcomePanel incidentId="INC-2841" />);
    expect(screen.getByText(/In progress\./)).toBeInTheDocument();
    expect(screen.getByText(/12\/30 stable cycles/)).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0); // before/after cells degraded, not thrown
  });
});
