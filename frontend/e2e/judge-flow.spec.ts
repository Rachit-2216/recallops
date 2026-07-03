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
  await page.goto("/app?demo=cloudflare");

  await expect(
    page.getByRole("heading", { name: /memory-assisted incident response/i }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /load Cloudflare outage case study/i })
    .click();
  await expect(page).toHaveURL(/\/app\/incidents\/CF-OUTAGE-2025-12-05/);
  await expect(
    page.getByText("CF-OUTAGE-2025-12-05", { exact: true }),
  ).toBeVisible();

  await page.getByRole("button", { name: /recall evidence/i }).click();
  await expect(
    page.getByText(/November 18 is the closest prior incident/i),
  ).toBeVisible();
  await expect(page.getByText(/global configuration propagation/i)).toBeVisible();
  await expect(page.getByText("referenced", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: /cloudflare-november-18-postmortem/i,
    }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "Path" }).click();
  await expect(page.getByText(/same distribution path: global configuration/i)).toBeVisible();
  await expect(page.getByText(/same blast-radius risk: fleet-wide propagation/i)).toBeVisible();

  await page
    .getByRole("button", {
      name: /unsafe-global-killswitch-assumption\.md/i,
    })
    .click();
  await page.getByRole("tab", { name: "Lifecycle" }).click();
  await page.getByRole("button", { name: "Forget memory" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByLabel(/confirmation phrase/i)
    .fill("FORGET unsafe-global-killswitch-assumption.md");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Forget memory" })
    .click();
  await expect(page.getByText(/Before · reference found/i)).toBeVisible();
  await expect(page.getByText(/After · no reference/i)).toBeVisible();
  await page.getByRole("button", { name: /close verified result/i }).click();

  await page
    .getByLabel("Root cause", { exact: true })
    .fill("A fleet-wide killswitch exposed a nil-handling bug in the FL1 rules module.");
  await page
    .getByLabel("Mitigation", { exact: true })
    .fill("Reverted the global configuration change and restored the prior ruleset state.");
  await page
    .getByLabel("Verification", { exact: true })
    .fill("All traffic was restored by 09:12 UTC and HTTP 500 errors returned to normal.");
  await page.getByLabel(/human confirmation/i).check();
  await page
    .getByRole("button", { name: /promote verified resolution/i })
    .click();
  await expect(page.getByText("promoted", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: /view proof report/i }).click();
  await expect(
    page.getByRole("heading", { name: /CF-OUTAGE-2025-12-05 resolution/i }),
  ).toBeVisible();
  const cleanProof = page.getByRole("region", {
    name: /clean-session retrieval proof/i,
  });
  await cleanProof
    .getByRole("button", { name: /prove in clean session/i })
    .click();
  await expect(
    cleanProof.getByText(/verified resolution for CF-OUTAGE-2025-12-05/i),
  ).toBeVisible();
  await expect(cleanProof.getByText(/Permanent-memory source:/i)).toContainText(
    "verified-resolution-cf-outage-2025-12-05.md",
  );
});
