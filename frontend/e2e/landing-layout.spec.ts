import { expect, test } from "@playwright/test";

test.use({
  viewport: { width: 1920, height: 960 },
});

test("keeps the complete hero headline inside the first desktop viewport", async ({
  page,
}) => {
  await page.goto("/app?demo=cloudflare");
  await page.evaluate(() => document.fonts.ready);

  const headline = page.getByRole("heading", {
    name: /turn incident evidence into operational memory/i,
  });
  await expect(headline).toBeVisible();

  const fit = await headline.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      bottom: rect.bottom,
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      viewportHeight: window.innerHeight,
    };
  });

  expect(fit.scrollWidth).toBeLessThanOrEqual(fit.clientWidth);
  expect(fit.bottom).toBeLessThanOrEqual(fit.viewportHeight - 24);
});

test("gives the hero headline a visible pointer-hover response", async ({
  page,
}) => {
  await page.goto("/app?demo=cloudflare");
  await page.evaluate(() => document.fonts.ready);

  const headline = page.getByRole("heading", {
    name: /turn incident evidence into operational memory/i,
  });
  const lead = headline.locator(".hero-title__lead");
  const restingColor = await lead.evaluate(
    (element) => getComputedStyle(element).color,
  );

  await headline.hover();
  await expect
    .poll(() => lead.evaluate((element) => getComputedStyle(element).color))
    .not.toBe(restingColor);
});
