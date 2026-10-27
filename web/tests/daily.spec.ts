import { expect, test } from "@playwright/test";

async function begin(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "开始探索", exact: true }).click();
  await page.getByRole("radio").first().check();
}
async function complete(page: import("@playwright/test").Page) {
  await begin(page);
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.getByRole("checkbox").nth(0).check();
  await page.getByRole("checkbox").nth(1).check();
  await page.getByRole("textbox").fill("我更在意双方仍然有选择的自由");
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.getByRole("region", { name: "持续讨论", exact: true })).toBeVisible();
}

test("stance, multiple reasons, persistent discussion and optional book navigation", async ({ page }) => {
  let bookRequests = 0, chatRequests = 0;
  page.on("request", (request) => {
    if (/\/api\/v1\/(recommendations|reading-handoffs)/.test(request.url())) bookRequests++;
    if (/\/conversations\/[^/]+\/messages$/.test(request.url()) && request.method() === "POST") chatRequests++;
  });
  await complete(page);
  const discussion = page.getByRole("region", { name: "持续讨论", exact: true });
  await expect(discussion.getByText("AI 演示 · Mock", { exact: true })).toBeVisible();
  await expect(discussion.locator(".message.assistant")).toContainText("你的判断会改变吗");
  await expect(discussion.getByRole("button", { name: "发送", exact: true })).toBeVisible();
  await discussion.getByRole("textbox").fill("现在我改变看法了，我反对控制别人的选择");
  await discussion.getByRole("button", { name: "发送", exact: true }).click();
  await expect(discussion.locator(".message.assistant")).toHaveCount(2);
  await expect(discussion.getByRole("button", { name: "停止回复", exact: true })).toHaveCount(0);
  expect(chatRequests).toBe(2);
  await page.reload();
  await expect(discussion.getByText("现在我改变看法了，我反对控制别人的选择", { exact: true })).toBeVisible();
  expect(chatRequests).toBe(2);
  const stored = await page.evaluate(() => JSON.stringify({ session: { ...sessionStorage }, local: { ...localStorage } }));
  expect(stored).not.toContain("我更在意双方");
  expect(stored).not.toContain("现在我改变看法");
  expect(bookRequests).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: `test-results/discussion-${test.info().project.name}.png`, fullPage: true });
  await page.getByRole("link", { name: "根据讨论推荐书", exact: true }).click();
  await expect(page).toHaveURL(/\/recommendations\?conversation_id=/);
  await expect(page.getByText("推荐书籍功能正在准备中。", { exact: false })).toBeVisible();
  expect(bookRequests).toBe(0);
  await page.getByRole("link", { name: "返回原来的讨论", exact: true }).click();
  await expect(discussion.getByText("现在我改变看法了，我反对控制别人的选择", { exact: true })).toBeVisible();
  expect(chatRequests).toBe(2);
});

test("failed answer retains input, revision creates a new exploration", async ({ page }) => {
  await begin(page);
  await page.getByRole("textbox").fill("想保留的补充");
  await page.route("**/explorations/*/answers", (route) => route.abort());
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.getByRole("region", { name: "每日一问", exact: true }).getByRole("alert")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveValue("想保留的补充");
  await page.unroute("**/explorations/*/answers");
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.reload();
  await expect(page.getByText("想保留的补充", { exact: false })).toBeVisible();
  const before = await page.evaluate(() => JSON.parse(sessionStorage.getItem("wqs.daily.exploration")!).id);
  await page.getByRole("button", { name: "修改第 1 步", exact: true }).click();
  await page.getByRole("button", { name: "恢复前面的答案", exact: true }).click();
  await page.getByRole("radio").nth(1).check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.getByRole("checkbox", { name: "对方应保留选择爱谁的自由", exact: true })).toBeVisible();
  expect(await page.evaluate(() => JSON.parse(sessionStorage.getItem("wqs.daily.exploration")!).id)).not.toBe(before);
});

test("stream failure is visible and explicit retry keeps the same client id", async ({ page }) => {
  let failedId = "";
  await page.route("**/conversations/*/messages", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    failedId = route.request().postDataJSON().client_message_id;
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: 'event: message_error\ndata: {"message_id":"test","error":{"code":"MODEL_UNAVAILABLE","message":"AI暂时不可用，请重试","retryable":true,"request_id":"test"}}\n\n' });
  });
  await complete(page);
  const discussion = page.getByRole("region", { name: "持续讨论", exact: true });
  await expect(discussion.getByRole("alert")).toContainText("AI暂时不可用");
  await page.unroute("**/conversations/*/messages");
  let retriedId = "";
  page.on("request", (request) => {
    if (/\/conversations\/[^/]+\/messages$/.test(request.url()) && request.method() === "POST") retriedId = request.postDataJSON().client_message_id;
  });
  await discussion.getByRole("button", { name: "重试上一条消息", exact: true }).click();
  await expect(discussion.locator(".message.assistant")).toContainText("你的判断会改变吗");
  expect(retriedId).toBe(failedId);
});
