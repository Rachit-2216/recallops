import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "./AppShell";

function renderWithRouter(component: React.ReactNode) {
  return render(<MemoryRouter>{component}</MemoryRouter>);
}

it("renders the orbital command deck with clear application navigation", () => {
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
  expect(screen.getByText(/offline memory/i)).toBeVisible();
});
