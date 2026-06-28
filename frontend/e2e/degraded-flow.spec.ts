import { expect, test } from "@playwright/test";

test("keeps local incident work truthful when memory is degraded", async ({
  page,
  request,
}) => {
  await request.post("/api/test/memory-failures", {
    data: { operations: ["health", "recall", "remember"] },
  });
  await page.goto("/app?demo=checkout");
  await page
    .getByRole("button", { name: /load checkout outage demo/i })
    .click();
  await expect(page).toHaveURL(/\/app\/incidents\/INC-2048/);

  const observation = "Operator confirms Redis misses remain elevated.";
  await page.getByLabel("Add observation", { exact: true }).fill(observation);
  await page
    .getByRole("button", { name: /add observation to session/i })
    .click();
  const observationEntry = page
    .getByRole("listitem")
    .filter({ hasText: observation });
  await expect(observationEntry.getByText(observation)).toBeVisible();
  await expect(
    observationEntry.getByText(/pending · not permanent/i),
  ).toBeVisible();
  await expect(
    observationEntry.getByRole("button", { name: /retry session write/i }),
  ).toBeVisible();

  await page.getByRole("button", { name: /recall evidence/i }).click();
  await expect(page.getByText(/recall unavailable/i)).toBeVisible();
  await expect(
    page.getByText(/memory is temporarily unavailable/i),
  ).toBeVisible();
  await expect(
    page.getByText(/INC-1842 is the closest prior incident/i),
  ).not.toBeVisible();

  const health = await request.get("/api/health");
  expect(health.ok()).toBeTruthy();
  const payload = await health.json();
  expect(payload.status).toBe("degraded");
  expect(payload.memory.reachable).toBe(false);
  expect(JSON.stringify(payload).toLowerCase()).not.toContain("api_key");

  await request.post("/api/test/memory-failures", {
    data: { operations: [] },
  });
});
