import { expect, test } from "@playwright/test";

test("completes the evidence-to-clean-session judge flow", async ({
  page,
  request,
}) => {
  await request.post("/api/test/memory-failures", {
    data: { operations: [] },
  });
  await request.post("/api/demo/seed", {
    headers: { "X-Demo-Admin-Token": "e2e-admin-token" },
  });
  await page.goto("/app?demo=checkout");

  await expect(
    page.getByRole("heading", { name: /memory-assisted incident response/i }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /load checkout outage demo/i })
    .click();
  await expect(page).toHaveURL(/\/app\/incidents\/INC-2048/);
  await expect(page.getByText("INC-2048", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /recall evidence/i }).click();
  await expect(page.getByText(/INC-1842 is the closest prior incident/i)).toBeVisible();
  await expect(page.getByText(/Redis session TTL behavior/i)).toBeVisible();
  await expect(page.getByText("referenced", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: /postmortem-inc-1842/i }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "Path" }).click();
  await expect(page.getByText(/same dependency: Redis/i)).toBeVisible();
  await expect(page.getByText(/same timing: immediately after deployment/i)).toBeVisible();

  await page
    .getByRole("button", { name: /stale-cache-reset-rule\.md/i })
    .click();
  await page.getByRole("tab", { name: "Lifecycle" }).click();
  await page.getByRole("button", { name: "Forget memory" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByLabel(/confirmation phrase/i)
    .fill("FORGET stale-cache-reset-rule.md");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Forget memory" })
    .click();
  await expect(page.getByText(/Before · reference found/i)).toBeVisible();
  await expect(page.getByText(/After · no reference/i)).toBeVisible();
  await page.getByRole("button", { name: /close verified result/i }).click();

  await page
    .getByLabel("Root cause", { exact: true })
    .fill("deploy-418 passed millisecond TTL values to a seconds-based adapter.");
  await page
    .getByLabel("Mitigation", { exact: true })
    .fill("Rolled back the TTL configuration and reissued affected sessions.");
  await page
    .getByLabel("Verification", { exact: true })
    .fill("Checkout p95 and Redis session misses returned to baseline.");
  await page.getByLabel(/human confirmation/i).check();
  await page
    .getByRole("button", { name: /promote verified resolution/i })
    .click();
  await expect(page.getByText("promoted", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: /view proof report/i }).click();
  await expect(
    page.getByRole("heading", { name: /INC-2048 resolution/i }),
  ).toBeVisible();
  const cleanProof = page.getByRole("region", {
    name: /clean-session retrieval proof/i,
  });
  await cleanProof
    .getByRole("button", { name: /prove in clean session/i })
    .click();
  await expect(
    cleanProof.getByText(/verified resolution for INC-2048/i),
  ).toBeVisible();
  await expect(cleanProof.getByText(/Permanent-memory source:/i)).toContainText(
    "verified-resolution-inc-2048.md",
  );
});
