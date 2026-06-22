import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DiagnosisView } from "@/lib/types";

const diagnosis: DiagnosisView = {
  available: true,
  incident_id: "INC-7731",
  origin_alert_id: "ALERT-7731",
  alert: {
    id: "ALERT-7731", source: "MAIA", kind: "fault_recurrence", machine_id: "MCH-L4-CONV",
    order_id: "PO-2841", fault_code: "F27", severity: "S2",
    message: "MAIA: Line 4 fault F27 repeating with rising vibration.",
    signals: { vibration_to: 7.4 }, detected_at: null, status: "triaged", resulted_in_incident: "INC-7731",
  },
  degradation_kind: "mechanical_drivetrain_fault",
  root_causes: [
    { cause: "Coupling misalignment from the recent motor replacement", likelihood: "primary", basis: "recent motor swap" },
    { cause: "Drive-end bearing degradation", likelihood: "latent", basis: "historical INC-1990" },
  ],
  recommended_intervention: { kind: "coupling_alignment", title: "Coupling-alignment correction", description: "Correct the coupling alignment." },
  contingency: { kind: "bearing_replacement", note: "If F27 recurs, replace bearing BR-6205." },
  diagnostic_confidence: 0.7,
  citations: [{ document_id: "DOC-ALIGN", section: "Acceptance" }],
  proposed_intervention: { id: "ITV-1", kind: "coupling_alignment", title: "Coupling-alignment correction", status: "PROPOSED" },
  accepted: false,
  state: "INTERVENTION_PROPOSED",
};

const acceptMutate = vi.fn();

vi.mock("@/lib/hooks", () => ({
  useDiagnosis: () => ({ data: diagnosis, isLoading: false, isError: false, refetch: () => {} }),
  useMe: () => ({ data: { role: "supervisor" } }),
  useRecoveryActions: () => ({ acceptDiagnosis: { mutate: acceptMutate, isPending: false } }),
}));

import { DiagnosisPanel } from "@/components/mission/diagnosis-panel";

describe("DiagnosisPanel", () => {
  it("shows ranked root causes and the proposed intervention", () => {
    render(<DiagnosisPanel incidentId="INC-7731" />);
    expect(screen.getByText(/Coupling misalignment from the recent motor replacement/)).toBeInTheDocument();
    expect(screen.getByText(/Drive-end bearing degradation/)).toBeInTheDocument();
    expect(screen.getAllByText(/Coupling-alignment correction/).length).toBeGreaterThan(0);
  });

  it("makes the approval scope explicit (accepting vs not authorizing)", () => {
    render(<DiagnosisPanel incidentId="INC-7731" />);
    expect(screen.getByText("You are accepting")).toBeInTheDocument();
    expect(screen.getByText("You are not authorizing")).toBeInTheDocument();
    expect(screen.getByText(/Any machine start \/ stop \/ restart/)).toBeInTheDocument();
  });

  it("lets a supervisor accept the diagnosis", () => {
    render(<DiagnosisPanel incidentId="INC-7731" />);
    screen.getByText(/Accept & record intervention/).click();
    expect(acceptMutate).toHaveBeenCalled();
  });
});
