/**
 * Stage 4 accessibility gate: axe-core WCAG 2.2 AA automated checks plus a
 * keyboard/focus smoke test, in both Arabic (RTL) and English (LTR).
 *
 * Usage:
 *   STOREFRONT_BASE_URL=http://127.0.0.1:3000 npm run check
 *
 * The demo identity harness signs in through the API once per run and attaches
 * the resulting session cookies, so customer and operator routes are checked in
 * their real signed-in state rather than as redirects to a login page.
 *
 * PLAYWRIGHT_CHROMIUM_EXECUTABLE can point at any installed Chromium.
 */
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { BROWSER, launchBrowser } from "./engine.mjs";

const require = createRequire(import.meta.url);
const AXE_SOURCE = await readFile(require.resolve("axe-core/axe.min.js"), "utf8");

const BASE_URL = process.env.STOREFRONT_BASE_URL ?? "http://127.0.0.1:3000";
const API_URL = process.env.SMART_ECOMMERCE_API_URL ?? "http://127.0.0.1:18000";
const PRODUCT_ID = "10000000-0000-4000-8000-000000000001";
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const AUTH_ROUTES = [
  ["catalog", "/"],
  ["product detail", `/products/${PRODUCT_ID}`],
  ["compare", "/compare"],
  ["cart", "/cart"],
  ["checkout", "/checkout"],
  ["assistant", "/assistant"],
  ["image search", "/search/image"],
  ["voice search", "/search/voice"],
  ["account", "/account"],
  ["account orders", "/account/orders"],
  ["account addresses", "/account/addresses"],
  ["back-office overview", "/backoffice"],
  ["back-office orders", "/backoffice/orders"],
  ["back-office inventory", "/backoffice/inventory"],
  ["back-office pricing", "/backoffice/pricing"],
  ["back-office segments", "/backoffice/segments"],
  ["back-office risk", "/backoffice/risk"],
  ["back-office analytics", "/backoffice/analytics"],
];

const GUEST_ROUTES = [
  ["sign in", "/login"],
  ["register", "/register"],
  ["back-office sign in", "/backoffice/login"],
];

const LOCALES = [
  ["ar", "rtl"],
  ["en", "ltr"],
];

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

const AUTH_COOKIES = [
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

const orderResponse = await fetch(`${API_URL}/v1/backoffice/orders?limit=1`, {
  headers: { authorization: `Bearer ${operatorToken}` },
});
if (orderResponse.ok) {
  const [firstOrder] = (await orderResponse.json()).items;
  if (firstOrder) {
    AUTH_ROUTES.push([
      "back-office order detail",
      `/backoffice/orders/${firstOrder.order_id}`,
    ]);
  }
}

// The customer order page carries the cancel form and the reorder control, so it
// needs its own check rather than relying on the operator detail being similar.
// A confirmed order keeps both controls rendered.
const customerOrders = await fetch(`${API_URL}/v1/orders?limit=50`, {
  headers: { authorization: `Bearer ${customerToken}` },
});
if (customerOrders.ok) {
  const items = (await customerOrders.json()).items;
  const cancellable = items.find((item) => item.status === "confirmed") ?? items[0];
  if (cancellable) {
    AUTH_ROUTES.push([
      "customer order detail",
      `/orders/${cancellable.order_id}`,
    ]);
  }
}


function serious(violations) {
  return violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
}

function describe(violation) {
  const targets = violation.nodes
    .slice(0, 3)
    .map((node) => node.target.join(" "))
    .join(" | ");
  return `${violation.id} (${violation.impact}): ${violation.help} -> ${targets}`;
}

async function verifyLocale(page, locale, direction) {
  const html = await page.evaluate(() => ({
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
  }));
  if (html.lang !== locale || html.dir !== direction) {
    throw new Error(
      `expected lang="${locale}" dir="${direction}", got lang="${html.lang}" dir="${html.dir}"`,
    );
  }
}

async function keyboardSmoke(page) {
  await page.evaluate(() => document.body.focus());
  const reached = await page.evaluate(() => {
    const active = document.activeElement;
    return active !== null && active !== document.body;
  });
  if (!reached) {
    await page.keyboard.press("Tab");
  }
  const state = await page.evaluate(() => {
    const active = document.activeElement;
    if (active === null || active === document.body) return null;
    const style = getComputedStyle(active);
    return {
      tag: active.tagName.toLowerCase(),
      name:
        active.getAttribute("aria-label") ??
        active.textContent?.trim().slice(0, 40) ??
        "",
      outlineWidth: parseFloat(style.outlineWidth || "0"),
      outlineStyle: style.outlineStyle,
      boxShadow: style.boxShadow,
    };
  });
  if (state === null) {
    throw new Error("Tab did not move focus to an interactive element");
  }
  const visible =
    (state.outlineWidth > 0 && state.outlineStyle !== "none") ||
    (state.boxShadow !== "none" && state.boxShadow !== "");
  if (!visible) {
    throw new Error(`focus is not visible on <${state.tag}> ${state.name}`);
  }
  return `${state.tag}:${state.name}`;
}

const browser = await launchBrowser();

const failures = [];
let checked = 0;

async function checkRoutes(context, locale, direction, routes) {
  for (const [name, path] of routes) {
    const page = await context.newPage();
    const url = `${BASE_URL}${path}`;
    try {
      const response = await page.goto(url, {
        waitUntil: "load",
        timeout: 30_000,
      });
      if (response !== null && response.status() >= 400) {
        throw new Error(`HTTP ${response.status()}`);
      }
      await verifyLocale(page, locale, direction);
      await page.addScriptTag({ content: AXE_SOURCE });
      const result = await page.evaluate(async (tags) => {
        return await window.axe.run(document, {
          runOnly: { type: "tag", values: tags },
          resultTypes: ["violations"],
        });
      }, WCAG_TAGS);

      const blocking = serious(result.violations);
      const minor = result.violations.filter(
        (violation) => !blocking.includes(violation),
      );
      for (const violation of blocking) {
        failures.push(`${locale} ${name} ${path}: ${describe(violation)}`);
      }
      for (const violation of minor) {
        console.warn(`warning ${locale} ${name}: ${describe(violation)}`);
      }
      checked += 1;
      console.log(
        `ok ${locale.padEnd(2)} ${name.padEnd(24)} ${path} ` +
          `(${result.violations.length} violations)`,
      );

      if (path === "/" && locale === "ar") {
        const focused = await keyboardSmoke(page);
        console.log(`ok keyboard focus reaches ${focused}`);
      }
    } catch (error) {
      failures.push(`${locale} ${name} ${path}: ${error.message}`);
      console.error(`fail ${locale} ${name} ${path}: ${error.message}`);
    } finally {
      await page.close();
    }
  }
}

try {
  for (const [locale, direction] of LOCALES) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce",
    });
    await context.addCookies([
      { name: "smart_ecommerce_locale", value: locale, url: BASE_URL },
      ...AUTH_COOKIES,
    ]);
    await checkRoutes(context, locale, direction, AUTH_ROUTES);
    await context.close();

    const guestContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce",
    });
    await guestContext.addCookies([
      { name: "smart_ecommerce_locale", value: locale, url: BASE_URL },
    ]);
    await checkRoutes(guestContext, locale, direction, GUEST_ROUTES);
    await guestContext.close();
  }
} finally {
  await browser.close();
}

console.log(`\n${checked} pages checked in ${BROWSER}, ${failures.length} blocking violations`);
if (failures.length > 0) {
  for (const failure of failures) console.error(` - ${failure}`);
  process.exit(1);
}
