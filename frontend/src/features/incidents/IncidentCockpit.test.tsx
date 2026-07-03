import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { IncidentCockpit } from "./IncidentCockpit";

const incidentDetail = {
  incident: {
    id: "CF-OUTAGE-2025-12-05",
    title: "Cloudflare HTTP 500 errors after a global WAF configuration change",
    severity: "SEV1",
    service: "Cloudflare FL1 proxy",
    status: "active",
    session_id: "incident:CF-OUTAGE-2025-12-05",
    started_at: "2025-12-05T08:47:00+00:00",
    resolved_at: null,
  },
  observations: [
    {
      id: "obs-1",
      incident_id: "CF-OUTAGE-2025-12-05",
      timestamp: "2025-12-05T08:47:00+00:00",
      source: "system",
      content: "A WAF configuration change propagated globally.",
      memory_status: "session_stored",
      memory_layer: "session",
      retry_count: 0,
    },
    {
      id: "obs-2",
      incident_id: "CF-OUTAGE-2025-12-05",
      timestamp: "2025-12-05T08:48:00+00:00",
      source: "system",
      content: "Approximately 28 percent of HTTP traffic returned errors.",
      memory_status: "session_stored",
      memory_layer: "session",
      retry_count: 0,
    },
    {
      id: "obs-3",
      incident_id: "CF-OUTAGE-2025-12-05",
      timestamp: "2025-12-05T08:50:00+00:00",
      source: "human",
      content: "Automated alerts declared the incident.",
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
        initialEntries={["/app/incidents/CF-OUTAGE-2025-12-05?demo=cloudflare"]}
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

  expect(await screen.findByText("CF-OUTAGE-2025-12-05")).toBeVisible();
  expect(screen.getByText("SEV1")).toBeVisible();
  expect(screen.getByText("Cloudflare FL1 proxy")).toBeVisible();
  expect(screen.getAllByText(/WAF configuration/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/28 percent/i)).toBeVisible();
  expect(screen.getByText(/automated alerts/i)).toBeVisible();
  expect(screen.getByLabelText(/^add observation$/i)).toBeVisible();
  expect(screen.getByLabelText(/recall question/i)).toHaveValue(
    "How is the December 5 outage related to the November 18 outage?",
  );
  expect(
    screen.getByRole("region", { name: /memory inspector/i }),
  ).toBeVisible();
});
