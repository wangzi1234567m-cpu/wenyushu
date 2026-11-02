import { expect, test, routeTestApi } from "./fixtures";

async function discuss(page: import("@playwright/test").Page) {
  await page.goto("/daily-question");
  await page.getByRole("button", { name: "开始探索", exact: true }).click();
  await page.getByRole("radio").first().check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  const chat = page.getByRole("region", { name: "持续讨论", exact: true });
  await expect(chat.getByRole("button", { name: "收藏AI 消息原文", exact: true })).toBeVisible();
  return chat;
}

test("original viewpoints persist, distinguish provenance and return to exact conversation without generation", async ({ page }) => {
  let generations = 0;
  page.on("request", (r) => { if (/\/conversations\/[^/]+\/messages$/.test(r.url()) && r.method() === "POST") generations++; });
  const chat = await discuss(page);
  await chat.getByRole("button", { name: "收藏AI 消息原文", exact: true }).click();
  await expect(chat.getByRole("button", { name: "取消收藏AI 消息原文", exact: true })).toHaveAttribute("aria-pressed", "true");
  const quote = "我想要自由，但又不想承担自由带来的风险。";
  await chat.getByRole("textbox").fill(quote);
  await chat.getByRole("button", { name: "发送", exact: true }).click();
  const user = chat.locator(".message.user").filter({ hasText: quote });
  await page.route("**/api/v1/saved-viewpoints", async (route) => {
    if (route.request().method() === "POST") await new Promise((resolve) => setTimeout(resolve, 750));
    await route.fallback();
  });
  await user.getByRole("button", { name: "收藏用户原话", exact: true }).click();
  await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "我的收藏", exact: true }).click();
  await expect(page.locator(".saved-viewpoint")).toHaveCount(2);
  await expect(page.getByText("用户原话", { exact: true })).toBeVisible();
  await expect(page.getByText("AI 观点 · 消息原文", { exact: true })).toBeVisible();
  await page.reload();
  const saved = page.locator(".saved-viewpoint").filter({ hasText: quote });
  await expect(saved).toBeVisible();
  const stored = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
  expect(stored).not.toContain(quote);
  const before = generations;
  await saved.getByRole("link", { name: "返回原讨论", exact: true }).click();
  await expect(page).toHaveURL(/\/discussion\/[^/?]+\?message_id=/);
  await expect(page.locator('.message[data-source="true"]')).toContainText(quote);
  expect(generations).toBe(before);
});

test("on-demand candidates cache, save as AI interpretation and cancel persistently", async ({ page }) => {
  let extractions = 0;
  page.on("request", (r) => { if (/\/conversations\/[^/]+\/viewpoints$/.test(r.url()) && r.method() === "POST") extractions++; });
  const chat = await discuss(page);
  expect(extractions).toBe(0);
  await chat.getByRole("button", { name: "提炼最近讨论的观点", exact: true }).click();
  const card = chat.locator(".viewpoint-card");
  await expect(card).toHaveCount(1);
  await expect(card.getByText("AI 提炼 · 非用户原话", { exact: true })).toBeVisible();
  await card.getByRole("button", { name: "收藏观点", exact: true }).click();
  await expect(card.getByRole("button", { name: "已收藏 · 取消收藏", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(chat.locator(".viewpoint-card").getByRole("button", { name: "已收藏 · 取消收藏", exact: true })).toBeVisible();
  expect(extractions).toBe(1);
  await expect(chat.getByRole("button", { name: "已提炼这段讨论", exact: true })).toBeDisabled();
  await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "我的收藏", exact: true }).click();
  await expect(page.locator(".saved-viewpoint")).toHaveCount(1);
  await expect(page.getByText("AI 提炼 · 非用户原话", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "取消收藏", exact: true }).click();
  await expect(page.getByRole("heading", { name: "还没有收藏的观点。", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "还没有收藏的观点。", exact: true })).toBeVisible();
});

test("collection loading failure recovers and another actor sees none", async ({ page, browser }) => {
  const chat = await discuss(page);
  await chat.getByRole("button", { name: "收藏AI 消息原文", exact: true }).click();
  await expect(chat.getByRole("button", { name: "取消收藏AI 消息原文", exact: true })).toBeVisible();
  await page.route("**/api/v1/saved-viewpoints?*", (route) => route.abort());
  await page.goto("/saved-viewpoints");
  await expect(page.getByRole("region", { name: "观点收藏", exact: true }).getByRole("alert")).toBeVisible();
  await page.unroute("**/api/v1/saved-viewpoints?*");
  await page.getByRole("button", { name: "重新加载收藏", exact: true }).click();
  await expect(page.locator(".saved-viewpoint")).toHaveCount(1);
  const other = await browser.newContext();
  const second = await other.newPage(); await routeTestApi(second);
  await second.goto("http://localhost:3000/saved-viewpoints");
  await expect(second.getByRole("heading", { name: "还没有收藏的观点。", exact: true })).toBeVisible();
  await second.unrouteAll({ behavior: "wait" }); await other.close();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: `test-results/viewpoints-${test.info().project.name}.png`, fullPage: true, scale: "css" });
});

test("failed extraction leaves chat usable and can retry explicitly", async ({ page }) => {
  const chat = await discuss(page);
  await page.route("**/conversations/*/viewpoints", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "MODEL_UNAVAILABLE", message: "暂时无法提炼，请重试", retryable: true, request_id: "test" } }) });
  });
  await chat.getByRole("button", { name: "提炼最近讨论的观点", exact: true }).click();
  await expect(chat.getByRole("region", { name: "讨论观点", exact: true }).getByRole("alert")).toContainText("暂时无法提炼");
  await expect(chat.getByRole("textbox")).toBeEnabled();
  await page.unroute("**/conversations/*/viewpoints");
  await chat.getByRole("button", { name: "提炼最近讨论的观点", exact: true }).click();
  await expect(chat.locator(".viewpoint-card")).toHaveCount(1);
});
