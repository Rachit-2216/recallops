import { render, screen, within } from "@testing-library/react";

import {
  EvidenceLibraryView,
  type EvidenceItem,
} from "./EvidenceLibrary";

const statuses: EvidenceItem["status"][] = [
  "queued",
  "processing",
  "ready",
  "failed",
  "forgotten",
];

const items = statuses.map((status, index) => ({
  data_id: `2b4f0ef0-1111-4111-8111-00000000000${index}`,
  dataset: "recallops_evidence_v1",
  name:
    status === "ready"
      ? "unsafe-global-killswitch-assumption.md"
      : `${status}-evidence.md`,
  kind: "runbook",
  source_uri: null,
  status,
  content_hash: `sha256:${index}`,
  source_date: "2026-06-20T00:00:00Z",
  is_stale: status === "ready",
  memory_layer: "permanent" as const,
}));

it("renders every ingestion state and keeps forgotten evidence in audit history", () => {
  render(<EvidenceLibraryView items={items} publicDemo />);

  for (const status of statuses) {
    expect(
      within(screen.getByTestId(`evidence-${status}`)).getByText(status, {
        exact: true,
      }),
    ).toBeVisible();
  }
  const forgotten = screen.getByTestId("evidence-forgotten");
  expect(forgotten).toHaveClass("evidence-card--forgotten");
  expect(
    within(forgotten).getByText(/excluded from active evidence/i),
  ).toBeVisible();
  expect(screen.getByText("Stale")).toBeVisible();
});

it("shows stable identity and permanent-memory metadata without public upload", () => {
  render(<EvidenceLibraryView items={items} publicDemo />);

  expect(screen.getAllByText(/2b4f0ef0/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/permanent/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/20 jun 2026/i).length).toBeGreaterThan(0);
  expect(
    screen.queryByRole("button", { name: /upload/i }),
  ).not.toBeInTheDocument();
});
