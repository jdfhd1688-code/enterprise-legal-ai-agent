/* Browser acceptance for Phase 3 evidence-first legal review. */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "docs", "images", "phase3");
const APP_URL = process.env.APP_URL || "http://127.0.0.1:8503";
const CHROME = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
fs.mkdirSync(OUT, { recursive: true });

async function shot(page, filename) {
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(OUT, filename), fullPage: false });
  console.log(`captured ${filename}`);
}

async function shotAt(page, locator, filename) {
  await locator.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, filename), fullPage: false });
  console.log(`captured ${filename}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto(APP_URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.getByText("LEGAL RISK CONTROL CENTER", { exact: true }).waitFor({ timeout: 30000 });
  await shot(page, "01_dashboard.png");

  await page.getByRole("button", { name: "新建审查", exact: true }).click();
  await page.getByRole("button", { name: /选择体验示例|已选择体验示例/ }).click();
  await page.getByRole("button", { name: "使用高风险示例", exact: true }).click();
  await page.getByRole("button", { name: "开始智能审查", exact: true }).click();
  await page.getByText("EXECUTIVE SUMMARY", { exact: true }).waitFor({ timeout: 90000 });
  const redline = page.getByText("Redline v1 · 修改前后对比", { exact: true }).first();
  if (!(await redline.isVisible())) {
    await page.getByText("查看判断依据 · Why this risk?", { exact: true }).first().click();
  }
  await redline.waitFor({ timeout: 30000 });
  await shotAt(page, redline, "02_evidence_redline.png");

  await page.getByText("查看技术处理详情", { exact: true }).click();
  await page.getByRole("tab", { name: "Legal Retrieval Debug", exact: true }).click();
  await page.getByText("RRF fusion result", { exact: true }).waitFor({ timeout: 30000 });
  await shotAt(page, page.getByText("RRF fusion result", { exact: true }), "03_retrieval_debug.png");

  await page.getByRole("button", { name: "进入人工复核", exact: true }).click();
  await page.getByText("LEGAL DECISION", { exact: true }).waitFor({ timeout: 30000 });
  await shotAt(page, page.getByText("AI 原始判断", { exact: true }), "04_human_review.png");
  await page.getByRole("button", { name: "保存复核结果", exact: true }).click();
  await page.waitForTimeout(1500);

  await page.getByRole("button", { name: "报告中心", exact: true }).click();
  await page.getByText("合同审查报告", { exact: true }).waitFor({ timeout: 30000 });
  await shotAt(page, page.getByText("风险摘要", { exact: true }).last(), "05_report_center.png");

  const body = await page.locator("body").innerText();
  if (!body.includes("企业 Playbook") || !body.includes("法律依据")) {
    throw new Error("report center is missing Phase 3 evidence labels");
  }
  await browser.close();
  console.log("PHASE3_BROWSER_ACCEPTANCE=PASS");
})().catch((error) => { console.error(error); process.exit(1); });
