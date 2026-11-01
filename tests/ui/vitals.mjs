/**
 * Rendering performance gate.
 *
 * The load suite in `tests/load` measures server-side p95. This measures what
 * the operator actually waits for: largest contentful paint, cumulative layout
 * shift, and long main-thread tasks, collected in the page with
 * `PerformanceObserver` rather than by instrumenting the app.
 *
 *   STOREFRONT_BASE_URL=http://127.0.0.1:3001 \
 *   SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 \
 *   node tests/ui/vitals.mjs
 *
 * Budgets follow the Core Web Vitals "good" thresholds. They are asserted, not
 * printed, so a regression fails the command. Set BROWSER=firefox to run the
 * same routes on the other engine.
 */
import { readFile } from "node:fs/promises";
import { writeFile, mkdir } from "node:fs/promises";
import { chromium, firefox } from "playwright-core";

const BASE_URL = process.env.STOREFRONT_BASE_URL ?? "http://127.0.0.1:3001";
const API_URL = process.env.SMART_ECOMMERCE_API_URL ?? "http://127.0.0.1:8000";
const BROWSER = process.env.BROWSER ?? "chromium";
const PRODUCT_ID = "10000000-0000-4000-8000-000000000001";

const BUDGET = { lcp: 2500, cls: 0.1, tbt: 200 };

// The heaviest surfaces: the largest catalog payload, the densest operator
// tables, and the one page that fans out over a date range.
const ROUTES = [
  ["catalog", "/"],
  ["product detail", `/products/${PRODUCT_ID}`],
  ["compare", "/compare"],
  ["cart", "/cart"],
  ["checkout", "/checkout"],
  ["back-office orders", "/backoffice/orders"],
  ["back-office analytics", "/backoffice/analytics"],
  ["back-office inventory", "/backoffice/inventory"],
];

const VIEWPORTS = [
  ["desktop", 1440, 1000],
  ["mobile", 390, 844],
];

async function demoToken(email, password, surface) {
  const response = await fetch(`${API_URL}/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password, surface }),
  });
  if (!response.ok) throw new Error(`login failed for ${email}: ${response.status}`);
  return (await response.json()).token;
}

const INIT_SCRIPT = `
window.__vitals = { lcp: 0, cls: 0, tbt: 0, longTasks: [], supported: {} };
try {
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) window.__vitals.lcp = entry.startTime;
  }).observe({ type: "largest-contentful-paint", buffered: true });
  window.__vitals.supported.lcp = true;
} catch {}
try {
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__vitals.cls += entry.value;
    }
  }).observe({ type: "layout-shift", buffered: true });
  window.__vitals.supported.cls = true;
} catch {}
/* The longtask entry type is Chromium-only. Firefox never fires it, so an
   observed zero there would read as a perfect score rather than an absent
   measurement. */
try {
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      window.__vitals.tbt += Math.max(0, entry.duration - 50);
      window.__vitals.longTasks.push(Math.round(entry.duration));
    }
  }).observe({ type: "longtask", buffered: true });
  window.__vitals.supported.tbt =
    PerformanceObserver.supportedEntryTypes.includes("longtask");
} catch {}
`;

const [customer, operator] = await Promise.all([
  demoToken("customer@example.invalid", "demo-customer-1", "customer"),
  demoToken("operator@example.invalid", "demo-operator-1", "operator"),
]);

const browser =
  BROWSER === "firefox"
    ? await firefox.launch()
    : await chromium.launch({
        executablePath:
          process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?? "/usr/bin/chromium",
        args: ["--no-sandbox"],
      });

const results = [];
const failures = [];

for (const [viewportName, width, height] of VIEWPORTS) {
  for (const locale of ["ar", "en"]) {
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "no-preference",
      locale: locale === "ar" ? "ar-EG" : "en-GB",
    });
    await context.addInitScript(INIT_SCRIPT);
    await context.addCookies([
      { name: "smart_customer_session", value: customer, url: BASE_URL, httpOnly: true, sameSite: "Lax" },
      { name: "smart_operator_session", value: operator, url: BASE_URL, httpOnly: true, sameSite: "Lax" },
      { name: "smart_ecommerce_locale", value: locale, url: BASE_URL },
    ]);

    for (const [name, path] of ROUTES) {
      const page = await context.newPage();
      try {
        await page.goto(`${BASE_URL}${path}`, { waitUntil: "load", timeout: 45000 });
        // Let the entry animations settle: LCP is final once the page is quiet,
        // and CLS keeps accumulating until the last shift.
        await page.waitForTimeout(2500);
        const vitals = await page.evaluate(() => {
          const v = window.__vitals ?? { lcp: 0, cls: 0, tbt: 0, longTasks: [], supported: {} };
          return {
            lcp: Math.round(v.lcp),
            cls: Number(v.cls.toFixed(4)),
            // \`null\` means the engine cannot measure it, which is not the same
            // claim as "zero long tasks".
            tbt: v.supported.tbt ? Math.round(v.tbt) : null,
            longTasks: v.longTasks.length,
          };
        });
        const verdict = {
          viewport: viewportName,
          locale,
          route: name,
          path,
          ...vitals,
          ok:
            vitals.lcp <= BUDGET.lcp &&
            vitals.cls <= BUDGET.cls &&
            (vitals.tbt === null || vitals.tbt <= BUDGET.tbt),
        };
        results.push(verdict);
        if (!verdict.ok) failures.push(verdict);
        const mark = verdict.ok ? "ok  " : "FAIL";
        console.log(
          `${mark} ${viewportName.padEnd(8)} ${locale} ${name.padEnd(22)} ` +
            `lcp=${String(vitals.lcp).padStart(5)}ms cls=${String(vitals.cls).padStart(6)} ` +
            `tbt=${vitals.tbt === null ? "  n/a" : String(vitals.tbt).padStart(4) + "ms"}`,
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        console.log(`FAIL ${viewportName} ${locale} ${name}: ${message}`);
        failures.push({ viewport: viewportName, locale, route: name, path, error: message });
      } finally {
        await page.close();
      }
    }
    await context.close();
  }
}

await browser.close();

await mkdir(new URL("./shots/", import.meta.url), { recursive: true });
await writeFile(
  new URL(`./shots/vitals-${BROWSER}.json`, import.meta.url),
  JSON.stringify(
    {
      browser: BROWSER,
      baseUrl: BASE_URL,
      capturedAt: new Date().toISOString(),
      budget: BUDGET,
      pages: results,
      failures: failures.length,
    },
    null,
    2,
  ),
);

const tbtSupported = results.some((r) => r.tbt !== null);
console.log(
  `\n${results.length} pages measured in ${BROWSER} ` +
    `(budget: LCP ≤ ${BUDGET.lcp}ms, CLS ≤ ${BUDGET.cls}, ` +
    `TBT ≤ ${BUDGET.tbt}ms${tbtSupported ? "" : " — not measurable in this engine"}) — ` +
    `${failures.length} over budget`,
);

process.exit(failures.length === 0 ? 0 : 1);
