/* Portfolio screenshot capture script (Playwright-core + local Chrome). */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const IMAGE_DIR = path.join(__dirname, "..", "docs", "images");
const APP_URL = process.env.APP_URL || "http://127.0.0.1:8501";
const CHROME = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
fs.mkdirSync(IMAGE_DIR, { recursive: true });

async function nav(page, label) {
  await page.locator("label").filter({ hasText: label }).first().click();
  await page.waitForTimeout(2000);
}

async function shot(page, filename) {
  await page.screenshot({ path: path.join(IMAGE_DIR, filename), fullPage: false });
  console.log("saved " + filename);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto(APP_URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(6000);
  console.log("title:", await page.title());

  await nav(page, "工作台总览");
  await shot(page, "dashboard.png");

  await nav(page, "合同审查");
  await page.waitForTimeout(1000);
  await shot(page, "contract_review.png");

  try {
    await page.getByRole("button", { name: "开始智能审查" }).first().click();
    await page.waitForTimeout(9000);
    await page.getByText("审查结果摘要", { exact: false }).first().waitFor({ timeout: 45000 });
    await page.waitForTimeout(2000);
  } catch (e) {
    console.log("risk run warning: " + e.message);
  }
  await shot(page, "risk_result.png");

  try {
    await page.getByRole("button", { name: "审计记录 / 处理轨迹" }).first().click();
    await page.waitForTimeout(1500);
  } catch (e) {
    console.log("audit click warning: " + e.message);
  }
  await shot(page, "audit_log.png");

  await nav(page, "人工复核");
  await page.waitForTimeout(1500);
  await shot(page, "human_review.png");

  await nav(page, "报告中心");
  await page.waitForTimeout(1500);
  await shot(page, "report_center.png");

  await browser.close();
  console.log("done");
})().catch((error) => { console.error(error); process.exit(1); });
