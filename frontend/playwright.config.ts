import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";

const workspace = path.resolve(import.meta.dirname, "..");
const windowsUvFallback =
  "C:\\Users\\Rachit Shrivastava\\AppData\\Roaming\\Python\\Python313\\Scripts\\uv.exe";
const uv =
  process.env.UV_PATH ??
  (process.platform === "win32" && existsSync(windowsUvFallback)
    ? windowsUvFallback
    : "uv");
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const useExternalServer = process.env.PLAYWRIGHT_EXTERNAL_SERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  retries: 1,
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: externalBaseUrl ?? "http://127.0.0.1:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: useExternalServer ? undefined : [
    {
      command: `"${uv}" run uvicorn recallops.main:app --app-dir backend/src --host 127.0.0.1 --port 8000`,
      cwd: workspace,
      env: {
        APP_ENV: "test",
        APP_DATABASE_URL: "sqlite+aiosqlite:///./recallops-e2e.db",
        APP_DEMO_MODE: "true",
        APP_DEMO_BOOTSTRAP: "true",
        APP_DEMO_ADMIN_TOKEN: "e2e-admin-token",
        APP_E2E_MODE: "true",
        APP_COGNEE_MODE: "fake",
      },
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      cwd: import.meta.dirname,
      url: "http://127.0.0.1:5173/app",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
