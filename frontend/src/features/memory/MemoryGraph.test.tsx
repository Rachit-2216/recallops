import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import {
  MemoryGraph,
  type MemoryEdge,
  type MemoryNode,
} from "./MemoryGraph";

const nodes: MemoryNode[] = [
  { id: "deploy", label: "deploy-418", kind: "deployment" },
  { id: "ttl", label: "session TTL configuration", kind: "dependency" },
  { id: "redis", label: "Redis sessions", kind: "dependency" },
  { id: "misses", label: "session misses", kind: "symptom" },
  { id: "prior", label: "INC-1842", kind: "incident" },
  { id: "flush", label: "flush all Redis cache", kind: "resolution" },
];

const edges: MemoryEdge[] = [
  {
    id: "edge-changed",
    source: "deploy",
    target: "ttl",
    label: "changed",
    evidenceDataId: "evidence-deploy",
  },
  {
    id: "edge-affects",
    source: "ttl",
    target: "redis",
    label: "affects",
    evidenceDataId: "evidence-postmortem",
  },
  {
    id: "edge-caused",
    source: "redis",
    target: "misses",
    label: "caused",
    evidenceDataId: "evidence-errors",
  },
  {
    id: "edge-resembles",
    source: "misses",
    target: "prior",
    label: "resembles",
    evidenceDataId: "evidence-postmortem",
  },
  {
    id: "edge-stale",
    source: "redis",
    target: "flush",
    label: "obsolete advice",
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

  expect(screen.getByText("deploy-418")).toBeVisible();
  expect(screen.getByText("changed")).toBeVisible();
  expect(screen.getByText("session TTL configuration")).toBeVisible();
  expect(screen.getByText("affects")).toBeVisible();
  expect(screen.getByText("Redis sessions")).toBeVisible();
  expect(screen.getByText("caused")).toBeVisible();
  expect(screen.getByText("session misses")).toBeVisible();
  expect(screen.getByText("resembles")).toBeVisible();
  expect(screen.getByText("INC-1842")).toBeVisible();

  fireEvent.click(screen.getByTestId("edge-changed"));
  expect(onEvidenceSelect).toHaveBeenCalledWith("evidence-deploy");
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
  expect(screen.getByText("Redis sessions")).toBeVisible();
  expect(screen.getByTestId("edge-caused")).toBeVisible();
});
