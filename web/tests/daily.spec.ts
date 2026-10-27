import { expect, test } from "@playwright/test";

async function begin(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "开始探索", exact: true }).click();
  await page.getByRole("radio", { name: "我更认同前一种想法", exact: true }).check();
}

test("daily exploration, restore, explicit recommendation and revision", async ({ page }) => {
  let recommendationPosts = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/v1/recommendations") && request.method() === "POST") recommendationPosts++;
  });
  await begin(page);
  await page.getByRole("textbox").fill("我想从一个故事理解关系与选择");
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.reload();
  await expect(page.getByText("我想从一个故事理解关系与选择", { exact: false })).toBeVisible();
  await page.getByRole("radio", { name: "更关注人与人的关系", exact: true }).check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.getByRole("radio", { name: "都可以，跳过偏好", exact: true }).check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.getByRole("button", { name: "根据这些想法找书", exact: true })).toBeVisible();
  expect(recommendationPosts).toBe(0);
  await page.getByRole("button", { name: "根据这些想法找书", exact: true }).click();
  await expect(page.getByRole("heading", { name: "简·爱", exact: true })).toBeVisible();
  expect(recommendationPosts).toBe(1);
  await page.reload();
  await expect(page.getByRole("heading", { name: "简·爱", exact: true })).toBeVisible();
  expect(recommendationPosts).toBe(1);
  await page.getByRole("button", { name: "修改第 2 步", exact: true }).click();
  await page.route("**/explorations/*/answers", (route) => route.abort());
  await page.getByRole("button", { name: "恢复前面的答案", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.unroute("**/explorations/*/answers");
  await page.reload();
  await page.getByRole("button", { name: "恢复前面的答案", exact: true }).click();
  await page.getByRole("radio", { name: "更关注自己的自由与生活", exact: true }).check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.getByRole("radio", { name: "都可以，跳过偏好", exact: true }).check();
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await page.getByRole("button", { name: "根据这些想法找书", exact: true }).click();
  await expect(page.getByRole("heading", { name: "瓦尔登湖", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: `test-results/daily-${test.info().project.name}.png`, fullPage: true });
});

test("failed answer can retry without losing selection or supplementary text", async ({ page }) => {
  await begin(page);
  await page.getByRole("textbox").fill("想保留的补充");
  await page.route("**/explorations/*/answers", (route) => route.abort());
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveValue("想保留的补充");
  await page.unroute("**/explorations/*/answers");
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.getByRole("radio", { name: "更关注人与人的关系", exact: true })).toBeVisible();
});
