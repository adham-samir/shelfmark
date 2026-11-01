/**
 * UI capture harness: full-page screenshots and axe summaries for every route,
 * in Arabic (RTL) and English (LTR), at desktop, tablet, and mobile widths.
 *
 * The script signs in through the API with the seeded demo accounts and sets the
 * locale cookie the server actually reads, so a run produces both a real RTL
 * and a real LTR screenshot set.
 *
 * Usage:
 *   STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
 *     SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 \
 *     CAPTURE_LABEL=before npm run capture
 *
 * Output lands in `tests/ui/shots/<label>/` with a `summary.json` recording the
 * route, viewport, locale, and the serious/critical axe violation count so a
 * before/after comparison is a diff of two JSON files rather than an opinion.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { BROWSER, engineLabel, launchBrowser } from "../accessibility/engine.mjs";

const require = createRequire(import.meta.url);
const AXE_SOURCE = await readFile(require.resolve("axe-core/axe.min.js"), "utf8");

const BASE_URL = process.env.STOREFRONT_BASE_URL ?? "http://127.0.0.1:3000";
const API_URL = process.env.SMART_ECOMMERCE_API_URL ?? "http://127.0.0.1:8000";
const LABEL = engineLabel(process.env.CAPTURE_LABEL ?? "current");
const PRODUCT_ID = "10000000-0000-4000-8000-000000000001";
const OUT_DIR = new URL(`./shots/${LABEL}/`, import.meta.url);

const VIEWPORTS = [
  ["desktop", 1440, 1000],
  ["tablet", 900, 1000],
  ["mobile", 390, 844],
];

const LOCALES = [
  ["ar", "rtl"],
  ["en", "ltr"],
];

const SERIOUS = new Set(["serious", "critical"]);

async function sessionToken(email, password, surface) {
  const response = await fetch(`${API_URL}/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password, surface }),
  });
  if (!response.ok) {
    throw new Error(`demo sign-in failed for ${surface}: HTTP ${response.status}`);
  }
  return (await response.json()).token;
}

const [customerToken, operatorToken] = await Promise.all([
  sessionToken("customer@example.invalid", "demo-customer-1", "customer"),
  sessionToken("operator@example.invalid", "demo-operator-1", "operator"),
]);

const COOKIES = [
  {
    name: "smart_customer_session",
    value: customerToken,
    url: BASE_URL,
    httpOnly: true,
    sameSite: "Lax",
  },
  {
    name: "smart_operator_session",
    value: operatorToken,
    url: BASE_URL,
    httpOnly: true,
    sameSite: "Lax",
  },
];

// Routes that need a real record id are discovered rather than hard-coded, so a
// reseeded database does not silently turn a screenshot into a 404.
const routes = [
  ["catalog", "/"],
  ["catalog-filtered", "/?category=phones&availability=in_stock"],
  ["catalog-empty", "/?q=zzzznomatch"],
  ["product", `/products/${PRODUCT_ID}`],
  ["compare", `/compare?ids=${PRODUCT_ID}`],
  ["cart", "/cart"],
  ["checkout", "/checkout"],
  ["assistant", "/assistant"],
  ["image-search", "/search/image"],
  ["voice-search", "/search/voice"],
  ["account", "/account"],
  ["account-orders", "/account/orders"],
  ["account-addresses", "/account/addresses"],
  ["backoffice", "/backoffice"],
  ["backoffice-orders", "/backoffice/orders"],
  ["backoffice-inventory", "/backoffice/inventory"],
  ["backoffice-pricing", "/backoffice/pricing"],
  ["backoffice-segments", "/backoffice/segments"],
  ["backoffice-risk", "/backoffice/risk"],
  ["backoffice-analytics", "/backoffice/analytics"],
];

const guestRoutes = [
  ["login", "/login"],
  ["register", "/register"],
  ["backoffice-login", "/backoffice/login"],
  ["not-found", "/this-route-does-not-exist"],
];

const customerOrders = await fetch(`${API_URL}/v1/orders?limit=20`, {
  headers: { authorization: `Bearer ${customerToken}` },
});
if (customerOrders.ok) {
  const items = (await customerOrders.json()).items;
  const target = items.find((item) => item.status === "confirmed") ?? items[0];
  if (target) routes.push(["order-detail", `/orders/${target.order_id}`]);
}

const operatorOrders = await fetch(`${API_URL}/v1/backoffice/orders?limit=1`, {
  headers: { authorization: `Bearer ${operatorToken}` },
});
if (operatorOrders.ok) {
  const [first] = (await operatorOrders.json()).items;
  if (first) {
    routes.push(["backoffice-order-detail", `/backoffice/orders/${first.order_id}`]);
  }
}

await mkdir(OUT_DIR, { recursive: true });

/* A cross-engine run does not need all 136 pages. `CAPTURE_ONLY` takes a
   comma-separated list of route names so a second engine can shoot the
   representative surfaces without re-capturing every route. */
const ONLY = process.env.CAPTURE_ONLY?.split(",")
  .map((name) => name.trim())
  .filter(Boolean);
const select = (list) =>
  ONLY ? list.filter(([name]) => ONLY.includes(name)) : list;
const selectedRoutes = select(routes);
const selectedGuestRoutes = select(guestRoutes);

const browser = await launchBrowser();

const summary = {
  label: LABEL,
  browser: BROWSER,
  baseUrl: BASE_URL,
  capturedAt: new Date().toISOString(),
  pages: [],
  totals: { pages: 0, serious: 0, critical: 0, moderate: 0, minor: 0 },
};

function record(entry) {
  summary.pages.push(entry);
  summary.totals.pages += 1;
  summary.totals.serious += entry.axe.serious;
  summary.totals.critical += entry.axe.critical;
  summary.totals.moderate += entry.axe.moderate;
  summary.totals.minor += entry.axe.minor;
}

async function audit(page) {
  await page.addScriptTag({ content: AXE_SOURCE });
  const results = await page.evaluate(async () =>
    // eslint-disable-next-line no-undef
    axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
    }),
  );
  const counts = { serious: 0, critical: 0, moderate: 0, minor: 0 };
  const ids = new Set();
  for (const violation of results.violations) {
    const impact = violation.impact ?? "minor";
    if (impact in counts) counts[impact] += 1;
    if (SERIOUS.has(impact)) ids.add(violation.id);
  }
  return { ...counts, ids: [...ids].sort() };
}

async function capture(context, name, path, locale, viewportName) {
  const page = await context.newPage();
  const entry = {
    route: name,
    path,
    locale,
    viewport: viewportName,
    status: null,
    axe: { serious: 0, critical: 0, moderate: 0, minor: 0, ids: [] },
    error: null,
  };
  try {
    // `networkidle` never settles: the back-office rail prefetches every sibling
    // route, so the fetch queue is permanently busy. Wait for the document, then
    // for fonts and layout to settle.
    const response = await page.goto(`${BASE_URL}${path}`, {
      waitUntil: "domcontentloaded",
      timeout: 45000,
    });
    entry.status = response?.status() ?? null;
    await page.evaluate(() => document.fonts.ready).catch(() => {});
    // Let entrance animations settle so screenshots are comparable between runs.
    await page.waitForTimeout(1200);
    await page.screenshot({
      path: new URL(`${name}--${locale}--${viewportName}.png`, OUT_DIR).pathname,
      fullPage: true,
    });
    entry.axe = await audit(page);
  } catch (error) {
    entry.error = String(error).split("\n")[0];
  } finally {
    await page.close();
  }
  return entry;
}

for (const [locale] of LOCALES) {
  for (const [viewportName, width, height] of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "reduce",
    });
    await context.addCookies([
      ...COOKIES,
      { name: "smart_ecommerce_locale", value: locale, url: BASE_URL },
    ]);

    for (const [name, path] of selectedRoutes) {
      const entry = await capture(context, name, path, locale, viewportName);
      record(entry);
      console.log(
        `${locale}/${viewportName}/${name} ${entry.status ?? "-"} axe=${entry.axe.serious}/${entry.axe.critical}${
          entry.error ? ` ERR ${entry.error}` : ""
        }`,
      );
    }

    // Guest routes render signed out, so they use a context without sessions.
    if (locale === "ar" && viewportName === "desktop") {
      const guest = await browser.newContext({
        viewport: { width, height },
        reducedMotion: "reduce",
      });
      await guest.addCookies([
        { name: "smart_ecommerce_locale", value: locale, url: BASE_URL },
      ]);
      for (const [name, path] of selectedGuestRoutes) {
        const entry = await capture(guest, name, path, locale, viewportName);
        record(entry);
        console.log(
          `${locale}/${viewportName}/${name} ${entry.status ?? "-"} axe=${entry.axe.serious}/${entry.axe.critical}`,
        );
      }
      await guest.close();
    }

    await context.close();
  }
}

await browser.close();

await writeFile(
  new URL("summary.json", OUT_DIR),
  `${JSON.stringify(summary, null, 2)}\n`,
);

console.log(
  `\n${summary.totals.pages} pages captured to tests/ui/shots/${LABEL}/ ` +
    `— serious ${summary.totals.serious}, critical ${summary.totals.critical}, ` +
    `moderate ${summary.totals.moderate}, minor ${summary.totals.minor}`,
);
