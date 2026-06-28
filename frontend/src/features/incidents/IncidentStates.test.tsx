import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { IncidentCockpit } from "./IncidentCockpit";

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

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderState(recallPayload: unknown, status = 200) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, options) => {
    if ((options?.method ?? "GET") === "POST") {
      return response(recallPayload, status);
    }
    return response(detail);
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/app/incidents/INC-2048?demo=checkout"]}>
        <Routes>
          <Route
            path="/app/incidents/:incidentId"
            element={<IncidentCockpit />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function recall() {
  fireEvent.click(
    await screen.findByRole("button", { name: /recall evidence/i }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

it("shows an explicit partial-memory state while indexing", async () => {
  renderState({
    answer: null,
    verification: "unverified",
    partial_memory: true,
    no_result: false,
  });
  await recall();
  expect(await screen.findByText(/partial memory/i)).toBeVisible();
  expect(screen.getByText(/indexing in progress/i)).toBeVisible();
});

it("shows a degraded banner while local observation controls remain operable", async () => {
  renderState(
    {
      error: {
        code: "MEMORY_PROVIDER_UNAVAILABLE",
        message:
          "Memory is temporarily unavailable. Your observation is saved locally.",
        retryable: true,
        request_id: "request-1",
      },
    },
    503,
  );
  await recall();
  expect(await screen.findByText(/recall unavailable/i)).toBeVisible();
  expect(screen.getByLabelText(/^add observation$/i)).toBeEnabled();
});

it("shows a no-memory state with an evidence link", async () => {
  renderState({
    answer: null,
    verification: "unverified",
    references: [],
    why_recalled: [],
    no_result: true,
    partial_memory: false,
  });
  await recall();
  expect(await screen.findByText("No matching memory")).toBeVisible();
  expect(
    screen.getByRole("link", { name: /inspect evidence library/i }),
  ).toHaveAttribute("href", "/app/evidence");
});

it("does not expose promotion for an unverified answer", async () => {
  renderState({
    answer: "A hypothesis without evidence.",
    verification: "unverified",
    references: [],
    why_recalled: [],
    no_result: false,
    partial_memory: false,
  });
  await recall();
  await waitFor(() =>
    expect(screen.getAllByText("unverified").length).toBeGreaterThan(0),
  );
  expect(
    screen.queryByRole("button", { name: /promote/i }),
  ).not.toBeInTheDocument();
});
