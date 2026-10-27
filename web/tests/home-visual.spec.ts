import { expect, test } from "./fixtures";

test("editorial homepage, real images, semantic links and responsive layout", async ({ page }) => {
  let businessRequests = 0;
  const errors: string[] = [];
  page.on("request", (request) => { if (/\/api\/v1\/(explorations|conversations|recommendations)/.test(request.url())) businessRequests++; });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "首页", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("让一个好问题，");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("带你走向下一本书。");
  await expect(page.getByText("从问题走向阅读，于书中求索答案，衍生新的思考。", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "进入每日一问", exact: true })).toHaveAttribute("href", "/daily-question");
  await expect(page.getByRole("link", { name: "探索书籍", exact: true })).toHaveAttribute("href", "/discover");
  await expect(page.getByRole("heading", { name: "有些问题，值得慢慢聊。", exact: true })).toBeVisible();
  const photo = page.getByRole("img", { name: "雨滴映着城市暮色，两只手在温暖光线中轻轻靠近" });
  await expect(photo).toBeVisible();
  await expect.poll(() => photo.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await expect(page.getByRole("region", { name: "每日一问", exact: true })).toHaveCount(0);
  expect(businessRequests).toBe(0);
  await page.evaluate(() => document.fonts.ready);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const background = await page.locator(".thinking-entry").evaluate((element) => getComputedStyle(element).backgroundImage);
  expect(background).toContain("quiet-landscape.webp");
  const landscape = await page.request.get("/images/quiet-landscape.webp");
  expect(landscape.ok()).toBe(true);
  await page.screenshot({ path: `test-results/home-v1-${test.info().project.name}.png`, fullPage: true, scale: "css" });
  await page.getByRole("link", { name: "进入每日一问：爱，是否应该拥有选择的自由？", exact: true }).click();
  await expect(page).toHaveURL(/\/daily-question$/);
  await expect(page.getByRole("button", { name: "开始探索", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("book entry modes and independent discussion show honest preparation pages", async ({ page }) => {
  for (const [label, mode] of [["兴趣找书", "interest"], ["问题找书", "question"], ["目标学习", "learning"]]) {
    await page.goto("/");
    await page.getByRole("link", { name: new RegExp(`^${label}`) }).click();
    await expect(page).toHaveURL(new RegExp(`/discover\\?mode=${mode}$`));
    await expect(page.getByRole("heading", { name: label, exact: true })).toBeVisible();
    await expect(page.getByText(`${label}正在准备中。`, { exact: false })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "发现书籍", exact: true })).toHaveAttribute("aria-current", "page");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.goto("/");
  await page.getByRole("link", { name: "开启思辨", exact: true }).click();
  await expect(page).toHaveURL(/\/discussion$/);
  await expect(page.getByText("独立思辨入口正在准备中。", { exact: false })).toBeVisible();
  await page.getByRole("link", { name: "从每日一问聊起", exact: true }).click();
  await expect(page.getByRole("region", { name: "每日一问", exact: true })).toBeVisible();
});

test("legacy daily bookmark redirects to the independent page", async ({ page }) => {
  await page.goto("/#daily-question");
  await expect(page).toHaveURL(/\/daily-question$/);
  await expect(page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "每日一问", exact: true })).toHaveAttribute("aria-current", "page");
});
