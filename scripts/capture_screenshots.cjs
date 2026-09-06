/* Portfolio screenshot capture script (Playwright-core + local Chrome). */
const path = require("path");
const { chromium } = require("playwright-core");

const IMAGE_DIR = path.join(__dirname, "..", "docs", "images");
const APP_URL = process.env.APP_URL || "http://127.0.0.1:8501";
const CHROME =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

async function nav(page, label) {
  const item = page.locator("label").filter({ hasText: label }).first();
  await item.click();
  await page.waitForTimeout(2200);
}

async function shot(page, filename, label) {
  await page.screenshot({ path: path.join(IMAGE_DIR, filename), fullPage: true });
  console.log(`saved ${filename}: ${label}`);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: CHROME,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  await page.goto(APP_URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(5000);
  await page.waitForLoadState("networkidle").catch(() => {});
  console.log("app title:", await page.title());
  console.log("app body:", (await page.locator("body").innerText()).slice(0, 400).replace(/\n/g, " | "));

  await nav(page, "工作台总览");
  await page.waitForTimeout(1000);
  await shot(page, "dashboard.png", "dashboard");

  await nav(page, "合同审查");
  await page.waitForTimeout(1000);
  await shot(page, "contract_review.png", "contract review");

  const startButton = page.locator("button").filter({ hasText: "开始智能审查" }).first();
  if (await startButton.isVisible()) {
    await startButton.click();
    await page.waitForTimeout(6000);
  }
  await page.waitForSelector("text=审查结果摘要", { timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await shot(page, "risk_result.png", "risk result");

  const audit = page.locator("summary, button, [data-testid='stExpander']")
    .filter({ hasText: "审计记录 / 处理轨迹" }).first();
  await audit.click().catch(() => {});
  await page.waitForTimeout(1200);
  await shot(page, "audit_log.png", "audit log");

  await nav(page, "人工复核");
  await page.waitForTimeout(1200);
  await shot(page, "human_review.png", "human review");

  await nav(page, "报告中心");
  await page.waitForTimeout(1200);
  await shot(page, "report_center.png", "report center");

  await browser.close();
  console.log("done");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
