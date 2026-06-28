import { fireEvent, render, screen } from "@testing-library/react";

import type { EvidenceItem, RecallResult } from "../../api/recallops";
import { MemoryInspector } from "./MemoryInspector";

const referenced: RecallResult = {
  answer:
    "deploy-418 changed session TTL handling and resembles the verified INC-1842 Redis incident.",
  verification: "referenced",
  source: "graph",
  search_type: "GRAPH_COMPLETION_CONTEXT_EXTENSION",
  references: [
    {
      data_id: "f6d8b350-0d6b-58b3-a47f-f9755ef8893b",
      chunk_id: "chunk-postmortem-root-cause",
      document_name: "postmortem-inc-1842.md",
      snippet: "The missing conversion caused session TTL behavior to diverge.",
    },
  ],
  trace_id: "trace-2048",
  why_recalled: [
    "Same checkout service",
    "Same Redis dependency",
    "Same session-miss symptom",
    "Deploy occurred in the incident window",
  ],
  no_result: false,
  partial_memory: false,
};

const evidence: EvidenceItem[] = [
  {
    data_id: referenced.references[0].data_id,
    dataset: "recallops_evidence_v1",
    name: "postmortem-inc-1842.md",
    kind: "postmortem",
    source_uri: null,
    status: "ready",
    content_hash: "sha256:test",
    source_date: "2026-05-14T00:00:00Z",
    is_stale: false,
    memory_layer: "permanent",
  },
];

it("renders exact provenance and all four recall reasons", () => {
  render(<MemoryInspector evidenceItems={evidence} result={referenced} />);

  expect(screen.getByText("graph")).toBeVisible();
  expect(
    screen.getByText("GRAPH_COMPLETION_CONTEXT_EXTENSION"),
  ).toBeVisible();
  expect(
    screen.getAllByText("postmortem-inc-1842.md").length,
  ).toBeGreaterThan(0);
  expect(
    screen.getAllByText("chunk-postmortem-root-cause").length,
  ).toBeGreaterThan(0);
  expect(screen.getByText(/missing conversion caused/i)).toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: "Path" }));
  for (const reason of referenced.why_recalled) {
    expect(screen.getByText(reason)).toBeVisible();
  }
  expect(screen.getAllByText("referenced").length).toBeGreaterThan(0);

  fireEvent.click(
    screen.getByRole("button", { name: /postmortem-inc-1842/i }),
  );
  expect(screen.getByRole("tab", { name: "Evidence" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

it("labels an answer without references unverified and offers no promotion", () => {
  render(
    <MemoryInspector
      result={{
        ...referenced,
        verification: "unverified",
        references: [],
        why_recalled: [],
        trace_id: undefined,
      }}
    />,
  );

  expect(screen.getAllByText("unverified").length).toBeGreaterThan(0);
  expect(
    screen.queryByRole("button", { name: /promote/i }),
  ).not.toBeInTheDocument();
});
