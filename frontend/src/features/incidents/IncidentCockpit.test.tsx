import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { IncidentCockpit } from "./IncidentCockpit";

const incidentDetail = {
  incident: {
    id: "INC-2048",
    title: "Checkout latency and session failures after deploy-418",
    severity: "SEV1",
    service: "checkout-api",
    status: "active",
    session_id: "incident:INC-2048",
    started_at: "2026-06-28T08:10:00+00:00",
    resolved_at: null,
  },
  observations: [
    {
      id: "obs-1",
      incident_id: "INC-2048",
      timestamp: "2026-06-28T08:10:00+00:00",
      source: "system",
      content: "Checkout p95 latency exceeded 4 seconds.",
      memory_status: "session_stored",
      memory_layer: "session",
      retry_count: 0,
    },
    {
      id: "obs-2",
      incident_id: "INC-2048",
      timestamp: "2026-06-28T08:12:00+00:00",
      source: "system",
      content: "Redis session misses increased 640 percent.",
      memory_status: "session_stored",
      memory_layer: "session",
      retry_count: 0,
    },
    {
      id: "obs-3",
      incident_id: "INC-2048",
      timestamp: "2026-06-28T08:14:00+00:00",
      source: "human",
      content: "Symptoms began within ten minutes of deploy-418.",
      memory_status: "session_stored",
      memory_layer: "session",
      retry_count: 0,
    },
  ],
  recalls: [],
  memory_candidates: [],
  resolution: null,
  budget: { estimated_remaining: 14_000_000, protected_reserve: 6_000_000 },
};

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders the seeded incident signals and operator controls", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(incidentDetail), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/app/incidents/INC-2048?demo=checkout"]}
      >
        <Routes>
          <Route
            path="/app/incidents/:incidentId"
            element={<IncidentCockpit />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByText("INC-2048")).toBeVisible();
  expect(screen.getByText("SEV1")).toBeVisible();
  expect(screen.getByText("checkout-api")).toBeVisible();
  expect(screen.getAllByText(/deploy-418/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/4 seconds/i)).toBeVisible();
  expect(screen.getByText(/640 percent/i)).toBeVisible();
  expect(screen.getByLabelText(/^add observation$/i)).toBeVisible();
  expect(screen.getByLabelText(/recall question/i)).toHaveValue(
    "How is deploy-418 related to the previous Redis incident?",
  );
  expect(
    screen.getByRole("region", { name: /memory inspector/i }),
  ).toBeVisible();
});
