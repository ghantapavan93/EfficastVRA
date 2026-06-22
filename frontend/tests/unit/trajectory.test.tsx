import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecoveryTrajectory } from "@/components/charts/recovery-trajectory";
import type { TimelineCycle } from "@/lib/types";

const cycles: TimelineCycle[] = [
  { kind: "cycle", cycle_index: 16, window: "w1", at: null, vibration: 3.4, temperature: 69, cycle_time: 12.4, scrap_pct: 1.8, fault_code: null, source: "x", freshness_s: 2, is_recurrence: false },
  { kind: "cycle", cycle_index: 17, window: "w1", at: null, vibration: 6.8, temperature: 80, cycle_time: 14, scrap_pct: 3.6, fault_code: "F27", source: "x", freshness_s: 2, is_recurrence: true },
];

describe("RecoveryTrajectory", () => {
  it("exposes an accessible summary noting the cycle-17 recurrence", () => {
    const { getByRole } = render(
      <RecoveryTrajectory cycles={cycles} metric="vibration" label="Vibration RMS" unit="mm/s" threshold={4} baseline={3.1} />,
    );
    expect(getByRole("img").getAttribute("aria-label")).toMatch(/fault recurrence at cycle 17/);
  });

  it("shows an empty state when no cycles have been observed", () => {
    const { container } = render(
      <RecoveryTrajectory cycles={[]} metric="vibration" label="Vibration RMS" unit="mm/s" />,
    );
    expect(container.textContent).toMatch(/No cycles observed/);
  });
});
