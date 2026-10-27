import { expect, test } from "@playwright/test";

test("homepage, secure anonymous cookie, refresh and actor isolation", async ({ page, context, browser }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("走向一本好书");
  await expect(page.getByRole("status").filter({ hasText: "匿名访问已就绪" })).toHaveText("匿名访问已就绪");
  const cookie = (await context.cookies()).find((item) => item.name === "wqs_session")!;
  expect(cookie).toBeDefined();
  expect(cookie.httpOnly).toBe(true);
  expect(cookie.secure).toBe(true);
  expect(cookie.sameSite).toBe("Lax");
  expect(await page.evaluate(() => document.cookie)).not.toContain("wqs_session");
  await page.reload();
  await expect(page.getByRole("status").filter({ hasText: "匿名访问已就绪" })).toHaveText("匿名访问已就绪");
  expect((await context.cookies()).find((item) => item.name === "wqs_session")?.value).toBe(cookie.value);
  const other = await browser.newContext();
  const second = await other.newPage();
  await second.goto(page.url());
  await expect(second.getByRole("status").filter({ hasText: "匿名访问已就绪" })).toHaveText("匿名访问已就绪");
  expect((await other.cookies()).find((item) => item.name === "wqs_session")?.value).not.toBe(cookie.value);
  await other.close();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: `test-results/home-${test.info().project.name}.png`, fullPage: true });
});

test("bootstrap failure is recoverable", async ({ page }) => {
  await page.route("**/api/v1/auth/anonymous-session", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByRole("button", { name: "重新连接" })).toBeVisible();
  await page.unroute("**/api/v1/auth/anonymous-session");
  await page.getByRole("button", { name: "重新连接" }).click();
  await expect(page.getByRole("status").filter({ hasText: "匿名访问已就绪" })).toHaveText("匿名访问已就绪");
});
