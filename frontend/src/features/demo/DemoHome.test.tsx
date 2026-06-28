import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { DemoHome } from "./DemoHome";

function LocationProbe() {
  const location = useLocation();
  return <output aria-label="current route">{location.pathname}</output>;
}

function renderDemo() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route
            path="/app"
            element={
              <>
                <DemoHome />
                <LocationProbe />
              </>
            }
          />
          <Route
            path="/app/incidents/:incidentId"
            element={<LocationProbe />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

it("resets the synthetic incident and opens the checkout outage", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, options) => {
    const path = String(input);
    if (path === "/api/evidence") {
      return new Response(
        JSON.stringify({
          items: [
            {
              data_id: "evidence-1",
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
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    expect(path).toBe("/api/demo/reset");
    expect(options?.method).toBe("POST");
    return new Response(
      JSON.stringify({
        incident_id: "INC-2048",
        observation_count: 3,
        candidate_count: 1,
        synthetic: true,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  });

  renderDemo();
  fireEvent.click(
    screen.getByRole("button", { name: /load checkout outage demo/i }),
  );

  await waitFor(() =>
    expect(screen.getByLabelText("current route")).toHaveTextContent(
      "/app/incidents/INC-2048",
    ),
  );
});

it("never exposes an admin token field in public mode", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DemoHome publicDemo />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(
    await screen.findByText(/setup guidance/i),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText(/admin token/i)).not.toBeInTheDocument();
});
