import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  ConditionPill,
  EvidenceFreshnessBadge,
  SeverityIndicator,
  StateBadge,
} from "@/components/forge/badges";
import { SyntheticBadge } from "@/components/shell/synthetic-badge";

describe("state-bearing badges (color is never the only signal)", () => {
  it("renders a workflow state with a text label", () => {
    render(<StateBadge state="MONITORING_RECOVERY" />);
    expect(screen.getByText("Monitoring recovery")).toBeInTheDocument();
  });

  it("renders a violated condition with its label", () => {
    render(<ConditionPill status="VIOLATED" />);
    expect(screen.getByText("Violated")).toBeInTheDocument();
  });

  it("renders severity with a rank label", () => {
    render(<SeverityIndicator severity="S2" />);
    expect(screen.getByText(/S2/)).toBeInTheDocument();
  });

  it("marks stale evidence as stale when older than the freshness limit", () => {
    const { container } = render(<EvidenceFreshnessBadge seconds={9000} max={7200} />);
    expect(container.textContent).toMatch(/stale/);
  });

  it("does not mark fresh evidence as stale", () => {
    const { container } = render(<EvidenceFreshnessBadge seconds={30} max={7200} />);
    expect(container.textContent).not.toMatch(/stale/);
  });
});

describe("synthetic disclosure", () => {
  it("always discloses the synthetic, independent-prototype nature", () => {
    render(<SyntheticBadge />);
    expect(screen.getByText(/Independent Efficast-aligned prototype/i)).toBeInTheDocument();
  });
});
