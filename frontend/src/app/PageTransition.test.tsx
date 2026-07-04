import { render, screen } from "@testing-library/react";

import { PageTransition } from "./PageTransition";

it("keeps route content in the document while motion is applied", () => {
  render(
    <PageTransition routeKey="/app/evidence">
      <h1>Evidence library</h1>
    </PageTransition>,
  );

  expect(
    screen.getByRole("region", { name: /current workspace/i }),
  ).toHaveAttribute("data-route", "/app/evidence");
  expect(
    screen.getByRole("heading", { name: /evidence library/i }),
  ).toBeVisible();
});
