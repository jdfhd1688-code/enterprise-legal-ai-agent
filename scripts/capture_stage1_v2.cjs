/* Reproducible Stage 1 product UI acceptance capture. */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const IMAGE_DIR = path.join(__dirname, "..", "docs", "images", "stage1_v2");
const APP_URL = process.env.APP_URL || "http://127.0.0.1:8501";
const CHROME = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
fs.mkdirSync(IMAGE_DIR, { recursive: true });

async function nav(page, label) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.waitForTimeout(1000);
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
}

async function shot(page, filename) {
  await page.screenshot({ path: path.join(IMAGE_DIR, filename), fullPage: false });
  console.log("saved " + filename);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto(APP_URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.getByText("LEGAL RISK CONTROL CENTER", { exact: true }).waitFor({ timeout: 30000 });
  await shot(page, "01_dashboard.png");

  await nav(page, "新建审查");
  await page.getByText("选择合同来源", { exact: true }).first().waitFor();
  await shot(page, "02_new_review.png");
  await page.getByRole("button", { name: /选择体验示例|已选择体验示例/ }).click();
  await page.waitForTimeout(800);
  await shot(page, "03_new_review_selected.png");
  await page.getByRole("button", { name: "开始智能审查", exact: true }).click();
  await page.getByText("EXECUTIVE SUMMARY", { exact: true }).waitFor({ timeout: 60000 });
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
  await shot(page, "04_review_result.png");

  await nav(page, "待人工复核");
  const enterReview = page.getByRole("button", { name: "进入复核", exact: true }).first();
  if (await enterReview.isVisible()) {
    await enterReview.click();
    await page.getByText("LEGAL DECISION", { exact: true }).waitFor({ timeout: 30000 });
    await page.getByText("复核任务详情", { exact: true }).scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
  }
  await shot(page, "05_human_review.png");

  await nav(page, "报告中心");
  await page.getByText("报告列表", { exact: true }).waitFor({ timeout: 30000 });
  await shot(page, "06_report_center.png");
  await browser.close();
})().catch((error) => { console.error(error); process.exit(1); });
