import { chromium } from "playwright-core";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const DECK = `file://${ROOT}docs/presentation/deck.html`;
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?? "/usr/bin/chromium",
  args: ["--no-sandbox", "--allow-file-access-from-files"],
});
const failures = [];

for (const width of [1440, 960, 700]) {
  const height = width === 1440 ? 900 : width === 960 ? 640 : 1100;
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  await page.goto(DECK, { waitUntil: "load" });
  await page.waitForTimeout(300);

  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  if (overflow.scrollWidth > overflow.innerWidth + 1) {
    failures.push(`width ${width}: document overflows (${overflow.scrollWidth} > ${overflow.innerWidth})`);
  }

  const slides = await page.locator(".slide").count();
  for (let i = 0; i < slides; i += 1) {
    await page.evaluate((index) => {
      const nodes = Array.from(document.querySelectorAll(".slide"));
      nodes.forEach((node, position) => node.classList.toggle("active", position === index));
    }, i);
    await page.waitForTimeout(60);
    const box = await page.locator(".slide.active").boundingBox();
    if (!box || box.width < 100 || box.height < 100) {
      failures.push(`width ${width}: slide ${i + 1} is not rendered (${JSON.stringify(box)})`);
      continue;
    }
    if (box.x < -1 || box.y < -1 || box.x + box.width > width + 1 || box.y + box.height > height + 1) {
      failures.push(`width ${width}: slide ${i + 1} does not fit the viewport (${JSON.stringify(box)})`);
    }
    const clipped = await page.evaluate(() => {
      const slide = document.querySelector(".slide.active");
      return {
        scrollHeight: slide.scrollHeight,
        clientHeight: slide.clientHeight,
        scrollWidth: slide.scrollWidth,
        clientWidth: slide.clientWidth,
      };
    });
    if (clipped.scrollHeight > clipped.clientHeight + 2) {
      failures.push(`width ${width}: slide ${i + 1} content overflows vertically (${clipped.scrollHeight} > ${clipped.clientHeight})`);
    }
    if (clipped.scrollWidth > clipped.clientWidth + 2) {
      failures.push(`width ${width}: slide ${i + 1} content overflows horizontally (${clipped.scrollWidth} > ${clipped.clientWidth})`);
    }
  }

  await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll(".slide"));
    nodes.forEach((node, position) => node.classList.toggle("active", position === 0));
  });
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(150);
  const counter = await page.locator("#counter").textContent();
  if (!counter.startsWith("2 /")) failures.push(`width ${width}: arrow key did not advance (${counter})`);

  await page.keyboard.press("n");
  await page.waitForTimeout(100);
  const notesVisible = await page.locator("#notes").evaluate((node) => node.classList.contains("show"));
  if (!notesVisible) failures.push(`width ${width}: notes panel did not open`);

  const images = await page.evaluate(() =>
    Array.from(document.querySelectorAll("img")).map((img) => ({ src: img.getAttribute("src"), ok: img.complete && img.naturalWidth > 0 })),
  );
  for (const image of images) {
    if (!image.ok) failures.push(`width ${width}: image ${image.src} did not load`);
  }

  console.log(`width ${width}: ${slides} slides checked, ${images.length} images`);
  await context.close();
}

await browser.close();
if (failures.length) {
  for (const failure of failures) console.error(` - ${failure}`);
  process.exit(1);
}
console.log("deck layout verified");
