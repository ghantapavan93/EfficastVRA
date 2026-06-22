import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConditionRow } from "@/components/contract/condition-row";
import type { Condition } from "@/lib/types";

const vibration: Condition = {
  key: "vibration_rms",
  label: "Vibration RMS",
  op: "<=",
  threshold: 4.0,
  unit: "mm/s",
  baseline: 3.1,
  current_value: 3.6,
  status: "PASSING",
  sensor_tag: "VIB-L4-01",
  fault_code: null,
  deadline_kind: "cycles",
  deadline_value: 10,
  policy_ref: "RC-1042 · C1",
  rationale: "RMS must fall below 4.0 mm/s within 10 cycles.",
};

const fault: Condition = {
  ...vibration,
  key: "fault_f27",
  label: "Fault F27 non-recurrence",
  op: "not_recur",
  threshold: null,
  fault_code: "F27",
  current_value: 1,
  status: "VIOLATED",
  deadline_kind: "window",
  deadline_value: null,
  policy_ref: "RC-1042 · C3",
};

describe("RecoveryConditionRow", () => {
  it("shows metric, target, current value, source and status", () => {
    render(<ConditionRow c={vibration} />);
    expect(screen.getByText("Vibration RMS")).toBeInTheDocument();
    expect(screen.getByText(/≤ 4 mm\/s/)).toBeInTheDocument();
    expect(screen.getByText(/3\.6 mm\/s/)).toBeInTheDocument();
    expect(screen.getByText("VIB-L4-01")).toBeInTheDocument();
    expect(screen.getByText("Passing")).toBeInTheDocument();
  });

  it("renders a violated fault non-recurrence condition", () => {
    render(<ConditionRow c={fault} />);
    expect(screen.getByText("Fault F27 non-recurrence")).toBeInTheDocument();
    expect(screen.getByText("Violated")).toBeInTheDocument();
    expect(screen.getByText("1 recurrence")).toBeInTheDocument();
  });
});
