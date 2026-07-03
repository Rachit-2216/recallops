import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { ResolutionPanel } from "./ResolutionPanel";

function renderPanel(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function completeForm() {
  fireEvent.change(screen.getByLabelText(/^root cause$/i), {
    target: { value: "A global killswitch exposed nil handling in FL1." },
  });
  fireEvent.change(screen.getByLabelText(/^mitigation$/i), {
    target: { value: "Rolled back TTL configuration and reissued sessions." },
  });
  fireEvent.change(screen.getByLabelText(/^verification$/i), {
    target: { value: "Traffic was fully restored by 09:12 UTC." },
  });
  fireEvent.click(screen.getByLabelText(/human confirmation/i));
}

it("requires verified fields and prevents duplicate promotion while pending", async () => {
  let resolveRequest: ((value: {
    promotion_state: "promoted";
    confirmed_at: string;
  }) => void) | undefined;
  const onResolve = vi.fn(
    () =>
      new Promise<{
        promotion_state: "promoted";
        confirmed_at: string;
      }>((resolve) => {
        resolveRequest = resolve;
      }),
  );
  renderPanel(
    <ResolutionPanel
      incidentId="CF-OUTAGE-2025-12-05"
      onResolve={onResolve}
      traceIds={["trace-2048"]}
    />,
  );

  expect(screen.getByRole("button", { name: /promote verified resolution/i })).toBeDisabled();
  completeForm();
  const submit = screen.getByRole("button", {
    name: /promote verified resolution/i,
  });
  fireEvent.click(submit);

  expect(await screen.findByText("promotion_pending")).toBeVisible();
  expect(submit).toBeDisabled();
  expect(screen.queryByText(/learned/i)).not.toBeInTheDocument();

  resolveRequest?.({
    promotion_state: "promoted",
    confirmed_at: "2026-06-28T10:00:00Z",
  });
  expect((await screen.findAllByText("promoted")).length).toBeGreaterThan(0);
});

it("shows promotion_failed and allows an explicit retry", async () => {
  const onResolve = vi
    .fn()
    .mockRejectedValueOnce(new Error("Improve unavailable"))
    .mockResolvedValueOnce({
      promotion_state: "promoted",
      confirmed_at: "2026-06-28T10:00:00Z",
    });
  renderPanel(
    <ResolutionPanel
      incidentId="CF-OUTAGE-2025-12-05"
      onResolve={onResolve}
      traceIds={["trace-2048"]}
    />,
  );
  completeForm();
  fireEvent.click(
    screen.getByRole("button", { name: /promote verified resolution/i }),
  );

  expect(await screen.findByText("promotion_failed")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /retry promotion/i }));
  await waitFor(() => expect(onResolve).toHaveBeenCalledTimes(2));
  expect((await screen.findAllByText("promoted")).length).toBeGreaterThan(0);
});
