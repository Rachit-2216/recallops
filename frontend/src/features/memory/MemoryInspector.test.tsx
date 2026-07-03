import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { EvidenceItem, RecallResult } from "../../api/recallops";
import { MemoryInspector } from "./MemoryInspector";

const referenced: RecallResult = {
  answer:
    "November 18 is the closest prior incident because both outages used rapid global configuration propagation.",
  verification: "referenced",
  source: "graph",
  search_type: "GRAPH_COMPLETION_CONTEXT_EXTENSION",
  references: [
    {
      data_id: "f6d8b350-0d6b-58b3-a47f-f9755ef8893b",
      chunk_id: "chunk-postmortem-root-cause",
      document_name: "cloudflare-november-18-postmortem.md",
      snippet: "The feature file was rapidly propagated across the network.",
    },
  ],
  trace_id: "trace-2048",
  why_recalled: [
    "same operator: Cloudflare",
    "same distribution path: global configuration",
    "same failure pattern: configuration reached the fleet before health gates",
    "same blast-radius risk: fleet-wide propagation",
  ],
  no_result: false,
  partial_memory: false,
};

const evidence: EvidenceItem[] = [
  {
    data_id: referenced.references[0].data_id,
    dataset: "recallops_evidence_v1",
    name: "cloudflare-november-18-postmortem.md",
    kind: "postmortem",
    source_uri: "https://blog.cloudflare.com/18-november-2025-outage/",
    status: "ready",
    content_hash: "sha256:test",
    source_date: "2025-11-18T00:00:00Z",
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
    screen.getAllByText("cloudflare-november-18-postmortem.md").length,
  ).toBeGreaterThan(0);
  expect(
    screen.getAllByText("chunk-postmortem-root-cause").length,
  ).toBeGreaterThan(0);
  expect(screen.getByText(/rapidly propagated/i)).toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: "Path" }));
  for (const reason of referenced.why_recalled) {
    expect(screen.getByText(reason)).toBeVisible();
  }
  expect(screen.getAllByText("referenced").length).toBeGreaterThan(0);

  fireEvent.click(
    screen.getByRole("button", {
      name: /cloudflare-november-18-postmortem/i,
    }),
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

it("returns keyboard focus to the forget trigger after the dialog closes", async () => {
  render(<MemoryInspector evidenceItems={evidence} result={referenced} />);
  fireEvent.click(screen.getByRole("tab", { name: "Lifecycle" }));
  const trigger = screen.getByRole("button", { name: "Forget memory" });
  trigger.focus();
  fireEvent.click(trigger);

  expect(screen.getByLabelText(/confirmation phrase/i)).toHaveFocus();
  fireEvent.click(
    screen.getByRole("button", { name: /close forget dialog/i }),
  );
  await waitFor(() => expect(trigger).toHaveFocus());
});
