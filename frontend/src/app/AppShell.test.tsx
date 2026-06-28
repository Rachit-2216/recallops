import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "./AppShell";

function renderWithRouter(component: React.ReactNode) {
  return render(<MemoryRouter>{component}</MemoryRouter>);
}

it("reserves root and exposes the application navigation", () => {
  renderWithRouter(<AppShell />);

  expect(screen.getByRole("link", { name: /incidents/i })).toHaveAttribute(
    "href",
    "/app",
  );
  expect(screen.getByRole("link", { name: /evidence/i })).toHaveAttribute(
    "href",
    "/app/evidence",
  );
  expect(screen.getByText(/synthetic demo/i)).toBeVisible();
});
