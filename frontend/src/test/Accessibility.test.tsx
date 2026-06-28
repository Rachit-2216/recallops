import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, vi } from "vitest";
import { configureAxe } from "vitest-axe";

import { AppShell } from "../app/AppShell";
import type { EvidenceItem, RecallResult } from "../api/recallops";
import { IncidentCockpit } from "../features/incidents/IncidentCockpit";
import { ResolutionPanel } from "../features/incidents/ResolutionPanel";
import { ForgetDialog } from "../features/memory/ForgetDialog";
import { MemoryInspector } from "../features/memory/MemoryInspector";

const evidence: EvidenceItem = {
  data_id: "e720a10a-eea4-5cca-b747-faac6b1ad7c8",
  dataset: "recallops_evidence_v1",
  name: "postmortem-inc-1842.md",
  kind: "postmortem",
  source_uri: null,
  status: "ready",
  content_hash: "sha256:test",
  source_date: "2026-05-14T00:00:00Z",
  is_stale: false,
  memory_layer: "permanent",
};

const recall: RecallResult = {
  answer: "INC-1842 shares the Redis session-TTL failure mode.",
  verification: "referenced",
  source: "graph",
  search_type: "GRAPH_COMPLETION_CONTEXT_EXTENSION",
  references: [
    {
      data_id: evidence.data_id,
      chunk_id: "chunk-1",
      document_name: evidence.name,
      snippet: "Session misses followed the deployment.",
    },
  ],
  trace_id: "trace-1",
  why_recalled: [
    "Same service",
    "Same dependency",
    "Same symptom",
    "Same deployment window",
  ],
  no_result: false,
  partial_memory: false,
};

const detail = {
  incident: {
    id: "INC-2048",
    title: "Checkout outage after deploy-418",
    severity: "SEV1",
    service: "checkout-api",
    status: "active",
    session_id: "incident:INC-2048",
    started_at: "2026-06-28T08:10:00Z",
    resolved_at: null,
  },
  observations: [],
  recalls: [],
  memory_candidates: [],
  resolution: null,
  budget: { estimated_remaining: 14_000_000, protected_reserve: 6_000_000 },
};

const axe = configureAxe({
  rules: {
    "color-contrast": { enabled: false },
  },
});

function queryProvider(children: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("has no automated accessibility violations in the application shell", async () => {
  const { container } = render(
    <MemoryRouter>
      <AppShell />
    </MemoryRouter>,
  );
  expect((await axe(container)).violations).toEqual([]);
});

it("has no automated accessibility violations in the incident cockpit", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(detail), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const { container } = render(
    queryProvider(
      <MemoryRouter initialEntries={["/app/incidents/INC-2048"]}>
        <Routes>
          <Route
            path="/app/incidents/:incidentId"
            element={<IncidentCockpit />}
          />
        </Routes>
      </MemoryRouter>,
    ),
  );
  expect(await screen.findByText("INC-2048")).toBeVisible();
  expect((await axe(container)).violations).toEqual([]);
});

it("has no automated accessibility violations in the memory inspector", async () => {
  const { container } = render(
    <MemoryInspector evidenceItems={[evidence]} result={recall} />,
  );
  expect((await axe(container)).violations).toEqual([]);
});

it("has no automated accessibility violations in the forget dialog", async () => {
  const { container } = render(
    <ForgetDialog
      item={evidence}
      onClose={() => undefined}
      onForget={() =>
        Promise.resolve({
          data_id: evidence.data_id,
          status: "forgotten",
          before_reference_found: true,
          after_reference_found: false,
        })
      }
    />,
  );
  expect((await axe(container)).violations).toEqual([]);
});

it("has no automated accessibility violations in the resolution panel", async () => {
  const { container } = render(
    queryProvider(
      <MemoryRouter>
        <ResolutionPanel
          incidentId="INC-2048"
          onResolve={() =>
            Promise.resolve({
              promotion_state: "promoted",
              confirmed_at: "2026-06-28T10:00:00Z",
            })
          }
          traceIds={["trace-1"]}
        />
      </MemoryRouter>,
    ),
  );
  expect((await axe(container)).violations).toEqual([]);
});
