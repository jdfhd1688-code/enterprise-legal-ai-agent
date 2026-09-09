/* Browser acceptance capture for the real Stage 2 review workflow. */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const ROOT = path.join(__dirname, "..");
const IMAGE_DIR = path.join(ROOT, "docs", "images", "stage2_review");
const VIDEO_DIR = path.join(ROOT, "docs", "videos");
const APP_URL = process.env.APP_URL || "http://127.0.0.1:8501";
const CHROME = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const RECORD_VIDEO = process.env.RECORD_VIDEO === "1";
fs.mkdirSync(IMAGE_DIR, { recursive: true });
fs.mkdirSync(VIDEO_DIR, { recursive: true });

async function assertVisual(page, expectedAsset, viewportWidth = 1440) {
  const image = page.locator(".process-visual img");
  const src = await image.getAttribute("src");
  if (!src || !src.endsWith(expectedAsset)) {
    throw new Error(`expected ${expectedAsset}, received ${src}`);
  }
  const geometry = await image.evaluate((element) => ({
    clientRatio: element.clientWidth / element.clientHeight,
    naturalRatio: element.naturalWidth / element.naturalHeight,
    bodyWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  if (Math.abs(geometry.clientRatio - geometry.naturalRatio) > 0.04) {
    throw new Error(`image distortion at ${viewportWidth}px: ${JSON.stringify(geometry)}`);
  }
  if (geometry.bodyWidth > geometry.viewportWidth + 2) {
    throw new Error(`horizontal overflow at ${viewportWidth}px: ${JSON.stringify(geometry)}`);
  }
  console.log(`verified ${expectedAsset} at ${viewportWidth}px without distortion or overflow`);
}

async function waitStage(page, title, filename, expectedAsset, responsiveWidth) {
  await page.locator(".process-stage-title", { hasText: title }).waitFor({ timeout: 30000 });
  await assertVisual(page, expectedAsset);
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(IMAGE_DIR, filename), fullPage: false });
  console.log(`captured ${filename}: ${title}`);
  if (responsiveWidth) {
    await page.setViewportSize({ width: responsiveWidth, height: 1000 });
    await assertVisual(page, expectedAsset, responsiveWidth);
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const contextOptions = {
    viewport: { width: 1440, height: 1000 },
  };
  if (RECORD_VIDEO) {
    contextOptions.recordVideo = { dir: VIDEO_DIR, size: { width: 1440, height: 1000 } };
  }
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  await page.goto(APP_URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.getByText("LEGAL RISK CONTROL CENTER", { exact: true }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(IMAGE_DIR, "00_dashboard.png"), fullPage: false });
  await page.getByRole("button", { name: "新建审查", exact: true }).click();
  await page.getByText("用三步完成审查配置", { exact: true }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(IMAGE_DIR, "00_new_review.png"), fullPage: false });
  await page.getByRole("button", { name: /选择体验示例|已选择体验示例/ }).click();
  await page.getByRole("button", { name: "使用低风险示例", exact: true }).click();
  await page.getByRole("button", { name: "开始智能审查", exact: true }).click();

  await waitStage(page, "合同已接收", "01_xiezhi_receive.png", "stage1.png");
  await waitStage(page, "正在解析合同", "02_xiezhi_delivery.png", "stage1.png");
  await waitStage(page, "正在规划审查维度", "03_gaotao_review.png", "stage2.png", 1024);
  await waitStage(page, "正在检索法律依据", "04_legal_retrieval.png", "stage2.png");
  await waitStage(page, "正在分析合同风险", "05_risk_analysis.png", "stage3.png", 768);
  await waitStage(page, "审查完成", "06_review_completed.png", "stage4.png", 390);
  await page.getByText("EXECUTIVE SUMMARY", { exact: true }).waitFor({ timeout: 30000 });
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(IMAGE_DIR, "07_result_transition.png"), fullPage: false });
  console.log("captured 07_result_transition.png: modern result page");
  await page.getByRole("button", { name: "报告中心", exact: true }).click();
  await page.getByText("合同审查报告", { exact: true }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(IMAGE_DIR, "08_report_center.png"), fullPage: false });

  // Regression: high-risk tasks must still route into the Stage 1 Human Review workspace.
  await page.getByRole("button", { name: "新建审查", exact: true }).click();
  await page.getByRole("button", { name: "使用高风险示例", exact: true }).click();
  await page.getByRole("button", { name: "开始智能审查", exact: true }).click();
  await page.locator(".process-stage-title", { hasText: "需要人工复核" }).waitFor({ timeout: 30000 });
  await page.getByText("建议人工复核", { exact: true }).first().waitFor({ timeout: 30000 });
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(IMAGE_DIR, "09_risk_results.png"), fullPage: false });
  await page.getByRole("button", { name: "进入人工复核", exact: true }).click();
  await page.getByText("LEGAL DECISION", { exact: true }).waitFor({ timeout: 30000 });
  await page.locator('[data-testid="stMain"]').evaluate((element) => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(IMAGE_DIR, "10_human_review.png"), fullPage: false });
  console.log("verified high-risk routing: result notice -> Human Review");

  const video = RECORD_VIDEO ? page.video() : null;
  await page.close();
  await context.close();
  if (video) {
    const recorded = await video.path();
    const target = path.join(VIDEO_DIR, "stage2_review_flow.webm");
    fs.copyFileSync(recorded, target);
    console.log(`captured ${target}`);
  }
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
