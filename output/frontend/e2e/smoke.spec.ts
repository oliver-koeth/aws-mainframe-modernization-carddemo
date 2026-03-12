import { expect, test } from "@playwright/test";

test("renders the scaffold jobs route", async ({ page }) => {
  await page.goto("/jobs");

  await expect(page.getByRole("heading", { level: 1, name: "CardDemo Modernization" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Jobs placeholder" })).toBeVisible();
  await expect(page.getByText("Connected to /api/jobs. Current placeholder records:")).toBeVisible();
  await expect(page.getByRole("link", { name: "Jobs" })).toHaveClass(/active/);
});
