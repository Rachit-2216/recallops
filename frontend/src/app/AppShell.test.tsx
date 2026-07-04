import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { AppShell } from "./AppShell";

function renderWithRouter(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders the orbital command deck with live Cognee status", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        database: "ok",
        memory: {
          mode: "live",
          reachable: true,
          dataset_ready: true,
        },
        demo_mode: true,
        credit_guard: { protected_reserve: 6_000_000 },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  renderWithRouter(<AppShell />);

  expect(
    screen.getByRole("banner", { name: /recallops command deck/i }),
  ).toBeVisible();
  expect(
    screen.getByRole("banner", { name: /recallops command deck/i }),
  ).not.toContainElement(
    screen.getByRole("navigation", { name: /primary navigation/i }),
  );
  expect(screen.getByLabelText(/recallops home/i)).toBeVisible();
  expect(screen.getByRole("link", { name: /incidents/i })).toHaveAttribute(
    "href",
    "/app",
  );
  expect(screen.getByRole("link", { name: /evidence/i })).toHaveAttribute(
    "href",
    "/app/evidence",
  );
  expect(screen.getByRole("link", { name: /memory/i })).toHaveAttribute(
    "href",
    "/app/memory",
  );
  expect(screen.getByText(/public case study/i)).toBeVisible();
  expect(await screen.findByText(/cognee memory/i)).toBeVisible();
  expect(screen.getByText(/^connected$/i)).toBeVisible();
});
