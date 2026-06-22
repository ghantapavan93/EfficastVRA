import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MissionCard } from "@/components/mission/mission-card";
import type { MissionSummary } from "@/lib/types";

const mission: MissionSummary = {
  id: "INC-2841",
  title: "Packaging Line 4 conveyor-drive fault F27 (PO-2841)",
  objective: "Verify recovery.",
  machine: { id: "MCH-L4-CONV", code: "L4-CONV", name: "Conveyor Drive" },
  order: { id: "PO-2841", product: "Cap 20L", qty_remaining: 8420 },
  state: "INCIDENT_REOPENED",
  state_group: "reopened",
  stage: "verification",
  severity: "S2",
  next_action: "Approve contingency",
  owner: "supervisor",
  missing_evidence: 2,
  reopened_count: 1,
  fault_code: "F27",
  contract_no: "RC-1042",
  contract_version: 2,
  outcome_confidence: 20,
  opened_at: null,
  updated_at: null,
  is_active: true,
};

describe("MissionCard", () => {
  it("renders incident id, title and state in the compact row", () => {
    render(<MissionCard m={mission} />);
    expect(screen.getByText("INC-2841")).toBeInTheDocument();
    expect(screen.getByText(/conveyor-drive fault F27/)).toBeInTheDocument();
    expect(screen.getByText("Incident reopened")).toBeInTheDocument();
  });

  it("surfaces the reopened count", () => {
    render(<MissionCard m={mission} />);
    expect(screen.getByText(/reopened ×1/)).toBeInTheDocument();
  });

  it("renders a spacious prominent variant with the next action", () => {
    render(<MissionCard m={mission} prominent />);
    // next action appears in both the agent-activity indicator and the 'Next' line
    expect(screen.getAllByText("Approve contingency").length).toBeGreaterThan(0);
    expect(screen.getByText(/Open mission/)).toBeInTheDocument();
  });
});
