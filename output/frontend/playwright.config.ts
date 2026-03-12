import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  webServer: [
    {
      command:
        "../backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      reuseExistingServer: !process.env["CI"],
      timeout: 120 * 1000,
      url: "http://127.0.0.1:8000/health",
    },
    {
      command: "npm start -- --host 127.0.0.1 --port 4200",
      reuseExistingServer: !process.env["CI"],
      timeout: 120 * 1000,
      url: "http://127.0.0.1:4200/jobs",
    },
  ],
  use: {
    baseURL: "http://127.0.0.1:4200",
    trace: "on-first-retry",
  },
});
