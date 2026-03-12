import { expect, test } from "@playwright/test";

test("renders the scaffold jobs route", async ({ page }) => {
  await page.goto("/jobs");

  await expect(page.getByRole("heading", { level: 1, name: "CardDemo Modernization" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Jobs placeholder" })).toBeVisible();
  await expect(page.getByText("Connected to /api/jobs. Current placeholder records:")).toBeVisible();
  await expect(page.getByRole("link", { name: "Jobs" })).toHaveClass(/active/);
});

test("fetches scaffold JSON collections through the frontend proxy", async ({ page }) => {
  await page.goto("/jobs");

  const collections = await page.evaluate(async () => {
    const endpoints = ["/api/jobs", "/api/accounts", "/api/transactions"] as const;
    const responses = await Promise.all(
      endpoints.map(async (endpoint) => {
        const response = await fetch(endpoint, {
          headers: {
            Accept: "application/json",
          },
        });

        return {
          endpoint,
          contentType: response.headers.get("content-type"),
          ok: response.ok,
          payload: await response.json(),
        };
      }),
    );

    return responses;
  });

  expect(collections).toEqual([
    {
      endpoint: "/api/jobs",
      contentType: expect.stringContaining("application/json"),
      ok: true,
      payload: [],
    },
    {
      endpoint: "/api/accounts",
      contentType: expect.stringContaining("application/json"),
      ok: true,
      payload: [],
    },
    {
      endpoint: "/api/transactions",
      contentType: expect.stringContaining("application/json"),
      ok: true,
      payload: [],
    },
  ]);
});
