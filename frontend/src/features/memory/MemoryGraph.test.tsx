import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import {
  MemoryGraph,
  type MemoryEdge,
  type MemoryNode,
} from "./MemoryGraph";

const nodes: MemoryNode[] = [
  { id: "change", label: "global WAF config", kind: "deployment" },
  { id: "execute", label: "FL1 execute object", kind: "dependency" },
  { id: "nil", label: "nil dereference", kind: "dependency" },
  { id: "errors", label: "HTTP 500 errors", kind: "symptom" },
  { id: "prior", label: "November 18 outage", kind: "incident" },
  { id: "unsafe", label: "global killswitch is always safe", kind: "resolution" },
];

const edges: MemoryEdge[] = [
  {
    id: "edge-removed",
    source: "change",
    target: "execute",
    label: "removed",
    evidenceDataId: "evidence-change",
  },
  {
    id: "edge-triggered",
    source: "execute",
    target: "nil",
    label: "triggered",
    evidenceDataId: "evidence-postmortem",
  },
  {
    id: "edge-caused",
    source: "nil",
    target: "errors",
    label: "caused",
    evidenceDataId: "evidence-errors",
  },
  {
    id: "edge-resembles",
    source: "errors",
    target: "prior",
    label: "shares blast-radius risk",
    evidenceDataId: "evidence-postmortem",
  },
  {
    id: "edge-stale",
    source: "change",
    target: "unsafe",
    label: "unsafe assumption",
    evidenceDataId: "evidence-stale",
  },
];

it("renders the seeded evidence-backed causal path and opens an edge reference", () => {
  const onEvidenceSelect = vi.fn();
  render(
    <MemoryGraph
      edges={edges}
      nodes={nodes}
      onEvidenceSelect={onEvidenceSelect}
    />,
  );

  expect(screen.getByText("global WAF config")).toBeVisible();
  expect(screen.getByText("removed")).toBeVisible();
  expect(screen.getByText("FL1 execute object")).toBeVisible();
  expect(screen.getByText("triggered")).toBeVisible();
  expect(screen.getByText("nil dereference")).toBeVisible();
  expect(screen.getByText("caused")).toBeVisible();
  expect(screen.getByText("HTTP 500 errors")).toBeVisible();
  expect(screen.getByText("shares blast-radius risk")).toBeVisible();
  expect(screen.getByText("November 18 outage")).toBeVisible();
  expect(
    screen.getByRole("list", {
      name: /evidence-backed relationship list/i,
    }),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: /fit view/i })).toBeVisible();

  fireEvent.click(screen.getByTestId("edge-removed"));
  expect(onEvidenceSelect).toHaveBeenCalledWith("evidence-change");
});

it("removes only the forgotten stale edge and preserves shared nodes", () => {
  const { rerender } = render(
    <MemoryGraph edges={edges} nodes={nodes} onEvidenceSelect={() => undefined} />,
  );
  expect(screen.getByTestId("edge-stale")).toBeVisible();

  rerender(
    <MemoryGraph
      edges={edges}
      excludedEvidenceIds={new Set(["evidence-stale"])}
      nodes={nodes}
      onEvidenceSelect={() => undefined}
    />,
  );

  expect(screen.queryByTestId("edge-stale")).not.toBeInTheDocument();
  expect(screen.getByText("global WAF config")).toBeVisible();
  expect(screen.getByTestId("edge-caused")).toBeVisible();
});
