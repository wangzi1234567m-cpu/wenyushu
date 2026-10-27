import { test as base, expect, type Page } from "@playwright/test";

// Native visual checks can use a separate Mock API without restarting the user's real API.
// CI's Compose API already defaults to Mock and needs no override.
export async function routeTestApi(page: Page) {
  const target = process.env.E2E_API_TARGET;
  if (!target) return;
  await page.route("**/api/v1/**", async (route) => {
    const original = new URL(route.request().url());
    const response = await route.fetch({ url: new URL(original.pathname + original.search, target).toString() });
    await route.fulfill({ response });
  });
}

export const test = base.extend({
  page: async ({ page }, providePage) => {
    await routeTestApi(page);
    await providePage(page);
    await page.unrouteAll({ behavior: "wait" });
  },
});
export { expect };
