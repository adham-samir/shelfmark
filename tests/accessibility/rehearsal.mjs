/**
 * Demo rehearsal: drives docs/demo-script.md through the real UI against a fresh
 * isolated stack, records timings, captures deck screenshots, and reports drift.
 */
import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const UI = process.env.DEMO_UI ?? "http://127.0.0.1:3100";
const API = process.env.DEMO_API ?? "http://127.0.0.1:18000";
const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const SHOTS = process.env.DEMO_SHOTS ?? `${ROOT}docs/presentation/assets`;
const PRODUCT = "10000000-0000-4000-8000-000000000001";
let CUSTOMER = {};
let OPERATOR = {};
let SESSION_COOKIES = [];

const log = [];
const drift = [];
const screenshots = [];
let t0 = Date.now();

function mark(step, note) {
  const seconds = (Date.now() - t0) / 1000;
  t0 = Date.now();
  log.push({ step, seconds: Number(seconds.toFixed(1)), note });
  console.log(`[${seconds.toFixed(1)}s] ${step}${note ? ` — ${note}` : ""}`);
}

async function guard(step, fn) {
  try {
    await fn();
  } catch (error) {
    drift.push({ step, error: String(error?.message ?? error).slice(0, 400) });
    console.log(`  DRIFT ${step}: ${error?.message ?? error}`);
  }
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${path} -> ${response.status} ${JSON.stringify(body)}`);
  return body;
}

async function shot(page, name, note = "") {
  const path = `${SHOTS}/${name}.png`;
  await page.screenshot({ path, animations: "disabled" });
  screenshots.push(name);
  console.log(`  shot ${name}${note ? ` (${note})` : ""}`);
}

async function settle(page) {
  await page.waitForLoadState("load");
  await page.waitForTimeout(150);
}

const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?? "/usr/bin/chromium",
  args: ["--no-sandbox"],
});

const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  reducedMotion: "reduce",
  locale: "ar-EG",
});
const page = await context.newPage();
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text().slice(0, 200));
});
page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message.slice(0, 200)}`));

await mkdir(SHOTS, { recursive: true });

try {
  // ------------------------------------------------------------------ step 0
  await guard("0. demo sign-in", async () => {
    const customer = await api("/v1/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: "customer@example.invalid",
        password: "demo-customer-1",
        surface: "customer",
      }),
    });
    const operator = await api("/v1/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: "operator@example.invalid",
        password: "demo-operator-1",
        surface: "operator",
      }),
    });
    CUSTOMER = { authorization: `Bearer ${customer.token}` };
    OPERATOR = { authorization: `Bearer ${operator.token}` };
    SESSION_COOKIES = [
      {
        name: "smart_customer_session",
        value: customer.token,
        url: UI,
        httpOnly: true,
        sameSite: "Lax",
      },
      {
        name: "smart_operator_session",
        value: operator.token,
        url: UI,
        httpOnly: true,
        sameSite: "Lax",
      },
    ];

    await page.goto(`${UI}/login`, { waitUntil: "load" });
    await page.fill("#auth-email", "customer@example.invalid");
    await page.fill("#auth-password", "demo-customer-1");
    await page.locator('.auth-form button[type="submit"]').click();
    await page.waitForURL(/\/account$/, { timeout: 30000 });

    await page.goto(`${UI}/backoffice/login`, { waitUntil: "load" });
    await page.fill("#auth-email", "operator@example.invalid");
    await page.fill("#auth-password", "demo-operator-1");
    await page.locator('.auth-form button[type="submit"]').click();
    await page.waitForURL(/\/backoffice$/, { timeout: 30000 });
  });
  mark("0. Demo sign-in — ID-01", "customer and operator sessions");

  // -------------------------------------------------------------- step 0b
  await guard("0b. password rotation", async () => {
    await page.goto(`${UI}/account`, { waitUntil: "load" });
    await settle(page);

    await page.fill("#current-password", "demo-customer-1");
    await page.fill("#new-password", "demo-customer-9");
    await page.fill("#confirm-password", "demo-customer-9");
    await page.locator('form:has(#current-password) button[type="submit"]').click();
    await page.waitForFunction(
      () => document.querySelector('form:has(#current-password) p[data-tone="success"]') !== null,
      null,
      { timeout: 30000 },
    );
    await shot(page, "27-password-changed");

    // The old value must stop working, and the new one must start.
    const oldLogin = await fetch(`${API}/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: "customer@example.invalid", password: "demo-customer-1" }),
    });
    if (oldLogin.status !== 401) throw new Error(`old password still accepted: ${oldLogin.status}`);
    const newLogin = await fetch(`${API}/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: "customer@example.invalid", password: "demo-customer-9" }),
    });
    if (newLogin.status !== 200) throw new Error(`new password rejected: ${newLogin.status}`);

    // Restore the seeded value so every later step keeps working.
    const rotated = await newLogin.json();
    const restore = await fetch(`${API}/v1/account/password`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${rotated.token}` },
      body: JSON.stringify({ current_password: "demo-customer-9", new_password: "demo-customer-1" }),
    });
    if (restore.status !== 200) throw new Error(`restore failed: ${restore.status}`);
    const back = await fetch(`${API}/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: "customer@example.invalid", password: "demo-customer-1" }),
    });
    if (back.status !== 200) throw new Error("seeded password not restored");
    CUSTOMER = { authorization: `Bearer ${(await back.json()).token}` };

    // Rotating a password ends every *other* session of that account, so the
    // restore above revoked the browser's own session. Sign the browser back in,
    // or every later step would run signed out.
    await page.goto(`${UI}/login`, { waitUntil: "load" });
    await page.fill("#auth-email", "customer@example.invalid");
    await page.fill("#auth-password", "demo-customer-1");
    await page.locator('.auth-form button[type="submit"]').click();
    await page.waitForURL(/\/account$/, { timeout: 30000 });
    const reseeded = await api("/v1/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: "customer@example.invalid", password: "demo-customer-1" }),
    });
    CUSTOMER = { authorization: `Bearer ${reseeded.token}` };
    SESSION_COOKIES[0].value = reseeded.token;
  });
  mark("0b. Password rotation — COM-10", "old rejected, new accepted, other sessions ended");

  // -------------------------------------------------------------- step 0c
  await guard("0c. saved addresses", async () => {
    await page.goto(`${UI}/account/addresses`, { waitUntil: "load" });
    await settle(page);

    // A previous run may have left an address behind; start from a known state.
    const existing = await api("/v1/addresses", { headers: CUSTOMER });
    for (const item of existing.items) {
      await api(`/v1/addresses/${item.address_id}`, {
        method: "DELETE",
        headers: CUSTOMER,
      });
    }
    await page.reload({ waitUntil: "load" });
    await settle(page);

    await page.fill("#address-label", "Rehearsal");
    await page.fill("#address-name", "Synthetic Customer");
    await page.fill("#address-phone", "+201000000055");
    await page.fill("#address-city", "Cairo");
    await page.fill("#address-line", "55 Rehearsal Street");
    await page.locator('form:has(#address-label) button[type="submit"]').click();
    await page.waitForFunction(
      () => document.querySelector('form:has(#address-label) p[data-tone="success"]') !== null,
      null,
      { timeout: 30000 },
    );

    let book = await api("/v1/addresses", { headers: CUSTOMER });
    const created = book.items.find((item) => item.label === "Rehearsal");
    if (!created) throw new Error("address not created");
    if (!created.is_default) throw new Error("first address is not the default");

    // Promote through the edit form, which is the supported way to move a default.
    const card = page.locator('section[aria-label="Rehearsal"]');
    await card.locator("button", { hasText: /تعديل|Edit/ }).first().click();
    await card.locator('input[name="is_default"]').check();
    await card.locator('button[type="submit"]').click();
    await page.waitForFunction(
      () => document.querySelector('section[aria-label="Rehearsal"] p[data-tone="success"]') !== null,
      null,
      { timeout: 30000 },
    );
    book = await api("/v1/addresses", { headers: CUSTOMER });
    if (!book.items.find((item) => item.label === "Rehearsal")?.is_default)
      throw new Error("promotion did not take effect");
    await shot(page, "28-address-book", `${book.items.length} saved`);

    // Delete it, so the demo stack keeps its starting state.
    // Saving an edit leaves the form open, so reload to return to the card view
    // where the delete control lives.
    await page.reload({ waitUntil: "load" });
    await settle(page);
    await page
      .locator('section[aria-label="Rehearsal"] button', { hasText: /حذف|Delete/ })
      .first()
      .click();
    await page.waitForTimeout(2000);
    book = await api("/v1/addresses", { headers: CUSTOMER });
    if (book.items.some((item) => item.label === "Rehearsal"))
      throw new Error("address was not deleted");
  });
  mark("0c. Saved addresses — COM-12", "created, promoted to default, deleted");

  // ------------------------------------------------------------------ step 1
  await guard("1. catalog discovery", async () => {
    await page.goto(`${UI}/`, { waitUntil: "load" });
    await settle(page);
    await page.locator(".toolbar select").nth(1).selectOption("24");
    await page.waitForURL(/size=24/);
    await settle(page);
    const cards = await page.locator(".product-grid .card").count();
    if (cards !== 13) throw new Error(`expected 13 product cards, saw ${cards}`);
    await shot(page, "01-catalog");

    await page.locator('.cat-list a[href*="category=phones"]').first().click();
    await page.waitForURL(/category=phones/);
    await settle(page);
    const phoneCards = await page.locator(".product-grid .card").count();
    if (phoneCards !== 5) throw new Error(`expected 5 phone cards, saw ${phoneCards}`);

    await page.locator(".check", { hasText: "128 GB" }).locator("input").click();
    await page.waitForURL(/f\.storage=128/);
    await settle(page);
    const filteredCards = await page.locator(".product-grid .card").count();
    if (filteredCards < 1 || filteredCards >= phoneCards)
      throw new Error(`storage filter did not narrow: ${filteredCards}`);
    const facets = await api("/v1/products/facets?category=phones&filter=storage%3A128%20GB");
    if (!facets.facets.some((f) => f.key === "storage"))
      throw new Error("facets missing storage group");
    await shot(page, "02-catalog-filtered", `${filteredCards} cards`);
  });
  mark("1. Storefront discovery — COM-01, SF-03", "catalog, category + attribute filter");

  // ------------------------------------------------------------------ image
  await guard("1b. image search", async () => {
    await page.goto(`${UI}/search/image`, { waitUntil: "load" });
    await settle(page);
    await page.selectOption("#image-category", "phones");
    await page.setInputFiles(
      "#image-file",
      `${ROOT}apps/storefront/public/products/phone-blue.png`,
    );
    await page.locator(".preview .btn-primary").click();
    await page.waitForSelector(".product-grid .card", { timeout: 30000 });
    const first = await page.locator(".product-grid .card a").first().getAttribute("href");
    if (!first?.includes(PRODUCT)) throw new Error(`first match was ${first}`);
    await page.locator(".product-grid .card").first().scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -140));
    await page.waitForTimeout(150);
    await shot(page, "03-image-search-results");

    // A text file named .png that the upload validator must reject. Written here
    // rather than assumed on disk, so the rehearsal runs on a clean machine.
    const spoofed = join(tmpdir(), "not-an-image.png");
    await writeFile(spoofed, "not a real image\n");
    await page.setInputFiles("#image-file", spoofed);
    await page.locator(".preview .btn-primary").click();
    await page.waitForSelector('.state[data-tone="error"]', { timeout: 30000 });
    await shot(page, "04-image-search-invalid");
  });
  mark("1b. Image search — SF-03", "known image first, spoofed PNG rejected");

  // ------------------------------------------------------------------ voice
  await guard("1c. voice search", async () => {
    await page.goto(`${UI}/search/voice`, { waitUntil: "load" });
    await settle(page);
    await page.locator(".mic-button").click();
    await page.waitForSelector('.state[data-tone="error"]', { timeout: 30000 });
    const heading = await page.locator('.state[data-tone="error"] h2').first().textContent();
    if (!heading?.trim()) throw new Error("denied state has no heading");
    await shot(page, "05-voice-denied", heading?.trim());
    await page.locator('.state[data-tone="error"] a[href="/"]').first().click();
    await page.waitForURL(`${UI}/`);
  });
  mark("1c. Voice search — SF-03", "microphone denial + text fallback");

  // ------------------------------------------------------------------ step 2
  let recommendationBasis;
  await guard("2. recommendations", async () => {
    await page.goto(`${UI}/products/${PRODUCT}`, { waitUntil: "load" });
    await settle(page);
    const rail = page.locator("#recommendations-heading");
    await rail.scrollIntoViewIfNeeded();
    await rail.waitFor({ timeout: 30000 });
    const railCards = await page.locator(".rail-card").count();
    if (railCards < 1) {
      const section = page.locator("section", {
        has: page.locator("#recommendations-heading"),
      });
      const notice = await section.innerText();
      if (!/شاهدت|seen every/.test(notice))
        throw new Error(`empty rail without exhausted state: ${notice.slice(0, 200)}`);
    }
    const section = page.locator("section", {
      has: page.locator("#recommendations-heading"),
    });
    await section.screenshot({
      path: `${SHOTS}/06-product-recommendations.png`,
      animations: "disabled",
    });
    screenshots.push("06-product-recommendations");
    console.log(`  shot 06-product-recommendations (${railCards} cards)`);
    const recs = await api("/v1/recommendations?limit=5", { headers: CUSTOMER });
    if (recs.strategy !== "hybrid") throw new Error(`strategy ${recs.strategy}`);
    if (recs.items.includes(PRODUCT)) throw new Error("seen item was recommended");
    recommendationBasis = recs.basis;
  });
  mark(
    "2. Recommendations — SF-01",
    recommendationBasis
      ? `hybrid, browsing ${recommendationBasis.browsing_events}, purchases ${recommendationBasis.purchased_items}`
      : "drift",
  );

  // ------------------------------------------------------------------ step 3
  let confirmedOrder;
  await guard("3. normal checkout", async () => {
    await page.goto(`${UI}/products/${PRODUCT}`, { waitUntil: "load" });
    await page.locator(".detail-actions .btn-primary").first().click();
    await page.waitForSelector(".add-to-cart [data-state='done']", { timeout: 30000 });

    await page.goto(`${UI}/cart`, { waitUntil: "load" });
    await settle(page);
    await shot(page, "07-cart");

    await page.goto(`${UI}/checkout`, { waitUntil: "load" });
    await settle(page);
    await page.fill("#recipient", "Synthetic Customer");
    await page.fill("#phone", "+201000000000");
    await page.fill("#city", "Cairo");
    await page.fill("#address", "12 Synthetic Test Street, Apt 4");
    await page.selectOption("#payment_token", "tok_sandbox_safe-1");
    await shot(page, "08-checkout");
    await page.locator('form.page-split button[type="submit"]').click();
    await page.waitForURL(/\/orders\//, { timeout: 30000 });
    await settle(page);
    const orderId = page.url().split("/orders/")[1];
    const order = await api(`/v1/orders/${orderId}`, { headers: CUSTOMER });
    if (order.status !== "confirmed") throw new Error(`order status ${order.status}`);
    const shipment = await api(`/v1/orders/${orderId}/shipment`, { headers: CUSTOMER });
    if (!shipment.events?.length) throw new Error("no shipment events");
    confirmedOrder = { id: orderId, unitPrice: order.items[0].unit_price };
    await shot(page, "09-order-confirmed", `status ${order.status}`);
  });
  mark(
    "3a. Cart + safe checkout — COM-02/03/04",
    confirmedOrder ? `order ${confirmedOrder.id.slice(0, 8)} confirmed` : "drift",
  );

  let reviewOrder;
  await guard("3b. high-risk checkout", async () => {
    await page.goto(`${UI}/products/${PRODUCT}`, { waitUntil: "load" });
    await page.locator(".detail-actions .btn-primary").first().click();
    await page.waitForSelector(".add-to-cart [data-state='done']", { timeout: 30000 });
    await page.goto(`${UI}/checkout`, { waitUntil: "load" });
    await settle(page);
    await page.fill("#recipient", "Synthetic Customer");
    await page.fill("#phone", "+201000000000");
    await page.fill("#city", "Cairo");
    await page.fill("#address", "12 Synthetic Test Street, Apt 4");
    await page.selectOption("#payment_token", "tok_sandbox_risk-high-1");
    await page.locator('form.page-split button[type="submit"]').click();
    await page.waitForURL(/\/orders\//, { timeout: 30000 });
    await settle(page);
    reviewOrder = { id: page.url().split("/orders/")[1] };
    const order = await api(`/v1/orders/${reviewOrder.id}`, { headers: CUSTOMER });
    if (order.status !== "review") throw new Error(`order status ${order.status}`);
    const shipment = await fetch(`${API}/v1/orders/${reviewOrder.id}/shipment`, {
      headers: CUSTOMER,
    });
    if (shipment.status !== 404) throw new Error("review order has a shipment");
    await shot(page, "10-order-review", "no shipment yet");
  });
  mark(
    "3b. High-risk checkout — BO-04",
    reviewOrder ? `order ${reviewOrder.id.slice(0, 8)} in review` : "drift",
  );

  await guard("3c. operator allow", async () => {
    await page.goto(`${UI}/backoffice/risk`, { waitUntil: "load" });
    await settle(page);
    await shot(page, "11-risk-queue");
    const queue = await api("/v1/backoffice/risk", { headers: OPERATOR });
    const item = queue.find((entry) => entry.order_id === reviewOrder?.id);
    if (!item) throw new Error("review order not in queue");
    const row = page.locator("tr", { hasText: reviewOrder.id.slice(0, 8) });
    const button = (await row.count()) ? row.locator(".risk-allow") : page.locator(".risk-allow").first();
    await button.click();
    let order;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      order = await api(`/v1/orders/${reviewOrder.id}`, { headers: CUSTOMER });
      if (order.status === "confirmed") break;
      await page.waitForTimeout(500);
    }
    if (order?.status !== "confirmed") throw new Error(`after allow: ${order?.status}`);
    const shipment = await api(`/v1/orders/${reviewOrder.id}/shipment`, { headers: CUSTOMER });
    if (!shipment.events?.length) throw new Error("allowed order has no shipment");
  });
  mark("3c. Risk review allow — BO-04", "audited allow, shipment created");

  await guard("3d. assessment failure", async () => {
    await page.goto(`${UI}/products/${PRODUCT}`, { waitUntil: "load" });
    await page.locator(".detail-actions .btn-primary").first().click();
    await page.waitForSelector(".add-to-cart [data-state='done']", { timeout: 30000 });
    await page.goto(`${UI}/checkout`, { waitUntil: "load" });
    await settle(page);
    await page.fill("#recipient", "Synthetic Customer");
    await page.fill("#phone", "+201000000000");
    await page.fill("#city", "Cairo");
    await page.fill("#address", "12 Synthetic Test Street, Apt 4");
    await page.selectOption("#payment_token", "tok_sandbox_risk-fail-1");
    await page.locator('form.page-split button[type="submit"]').click();
    await page.waitForURL(/\/orders\//, { timeout: 30000 });
    await settle(page);
    const orderId = page.url().split("/orders/")[1];
    const order = await api(`/v1/orders/${orderId}`, { headers: CUSTOMER });
    if (order.status !== "review") throw new Error(`order status ${order.status}`);
    const queue = await api("/v1/backoffice/risk", { headers: OPERATOR });
    const item = queue.find((entry) => entry.order_id === orderId);
    if (item?.outcome !== "assessment_failed")
      throw new Error(`outcome ${item?.outcome}`);
  });
  mark("3d. Assessment failure — BO-04", "routes to review, no completion");

  await guard("3e. model card", async () => {
    await page.goto(`${UI}/backoffice/risk`, { waitUntil: "load" });
    await settle(page);
    const card = await page.locator(".inventory-evidence").innerText();
    if (!/83\.3|0\.833|83/.test(card)) throw new Error("model card lacks recall");
    await shot(page, "12-risk-model", "model card + queue");
  });
  mark("3e. Model card — BO-04", "threshold, holdout metrics, limitations");

  // -------------------------------------------------------------- step 3f
  await guard("3f. buy again", async () => {
    if (!confirmedOrder?.id) throw new Error("no confirmed order to repeat");
    // Start from an empty cart so the count is unambiguous.
    const cart = await api("/v1/cart", { headers: CUSTOMER });
    for (const item of cart.items) {
      await api("/v1/cart/items", {
        method: "PUT",
        headers: { "content-type": "application/json", ...CUSTOMER },
        body: JSON.stringify({ product_id: item.product_id, quantity: 0 }),
      });
    }

    await page.goto(`${UI}/orders/${confirmedOrder.id}`, { waitUntil: "load" });
    await settle(page);
    await page.locator('section[aria-labelledby="order-reorder"] button[type="submit"]').click();
    await page.waitForFunction(
      () => document.querySelector('section[aria-labelledby="order-reorder"] p[data-tone="success"]') !== null,
      null,
      { timeout: 30000 },
    );
    const refilled = await api("/v1/cart", { headers: CUSTOMER });
    if (refilled.items.length !== 1) throw new Error(`cart has ${refilled.items.length} lines`);
    // Current price, not the checkout snapshot.
    const current = await api(`/v1/products/${PRODUCT}`);
    if (refilled.items[0].unit_price !== current.price.amount)
      throw new Error("reorder used the old price");
    await shot(page, "29-buy-again", `cart ${refilled.subtotal} EGP`);

    for (const item of refilled.items) {
      await api("/v1/cart/items", {
        method: "PUT",
        headers: { "content-type": "application/json", ...CUSTOMER },
        body: JSON.stringify({ product_id: item.product_id, quantity: 0 }),
      });
    }
  });
  mark("3f. Buy again — COM-13", "re-priced at current, cart refilled");

  // -------------------------------------------------------------- step 3g
  let lifecycleOrder;
  await guard("3g. operator lifecycle", async () => {
    // A fresh order, so the shipped/refunded states do not disturb step 5's
    // price-snapshot assertion on the earlier confirmed order.
    await api("/v1/cart/items", {
      method: "PUT",
      headers: { "content-type": "application/json", ...CUSTOMER },
      body: JSON.stringify({ product_id: "10000000-0000-4000-8000-000000000006", quantity: 1 }),
    });
    const placed = await api("/v1/checkout", {
      method: "POST",
      headers: { "content-type": "application/json", ...CUSTOMER },
      body: JSON.stringify({
        payment_token: "tok_sandbox_safe-rehearsal-lifecycle",
        idempotency_key: `rehearsal-lifecycle-${Date.now()}`,
        shipping: {
          recipient_name: "Synthetic Customer",
          phone: "+201000000000",
          city: "Cairo",
          address_line: "12 Synthetic Test Street, Apt 4",
        },
      }),
    });
    lifecycleOrder = { id: placed.order_id };
    if (placed.status !== "confirmed") throw new Error(`lifecycle order ${placed.status}`);

    await page.goto(`${UI}/backoffice/orders/${lifecycleOrder.id}`, { waitUntil: "load" });
    await settle(page);
    await shot(page, "30-operator-order", "queue detail with lifecycle controls");

    for (const target of ["ready", "in_transit"]) {
      await page.locator(`section[aria-labelledby="operator-lifecycle"] button[value="${target}"]`).click();
      await page.waitForTimeout(1800);
      await page.goto(`${UI}/backoffice/orders/${lifecycleOrder.id}`, { waitUntil: "load" });
      await settle(page);
    }
    const shipped = await api(`/v1/backoffice/orders/${lifecycleOrder.id}`, { headers: OPERATOR });
    if (shipped.status !== "shipped") throw new Error(`order status ${shipped.status}`);
    if (shipped.shipment.status !== "in_transit")
      throw new Error(`shipment status ${shipped.shipment.status}`);

    // A partial refund leaves the subtotal untouched.
    await page.locator('section[aria-labelledby="operator-lifecycle"] button', { hasText: /استرداد|Refund/ }).first().click();
    // The first form in this section is the shipment transition; the refund form
    // is the one that asks for an amount.
    const refundForm = page.locator(
      'section[aria-labelledby="operator-lifecycle"] form:has(input[name="amount"])',
    );
    await refundForm.locator('input[name="amount"]').fill("100");
    await refundForm.locator('input[name="reason"]').fill("Rehearsal partial refund");
    await refundForm.locator('button[type="submit"]').click();
    await page.waitForTimeout(2500);

    const refunded = await api(`/v1/backoffice/orders/${lifecycleOrder.id}`, { headers: OPERATOR });
    if (refunded.refund_total !== "100") throw new Error(`refund_total ${refunded.refund_total}`);
    if (refunded.subtotal !== shipped.subtotal) throw new Error("refund changed the subtotal");
    const history = refunded.adjustments;
    if (!history.length || history[0].kind !== "refund")
      throw new Error("adjustment history missing the refund");
    await shot(page, "31-operator-refund", `refunded ${refunded.refund_total} EGP`);
  });
  mark("3g. Operator lifecycle — COM-09", "ready -> in transit, partial refund audited");

  // ------------------------------------------------------------------ step 4
  await guard("4. inventory", async () => {
    await page.goto(`${UI}/backoffice/inventory`, { waitUntil: "load" });
    await settle(page);
    await page.locator(".inventory-run-button").click();
    await page.waitForSelector('p[data-tone="success"]', { timeout: 60000 });
    const first = await page.locator('p[data-tone="success"]').innerText();
    const firstNumbers = first.match(/\d+/g)?.map(Number) ?? [];
    await shot(page, "13-inventory-run", first);
    await page.locator(".inventory-run-button").click();
    await page.waitForFunction(
      (previous) => {
        const node = document.querySelector('p[data-tone="success"]');
        return node !== null && node.textContent !== previous;
      },
      first,
      { timeout: 60000 },
    );
    const second = await page.locator('p[data-tone="success"]').innerText();
    const secondNumbers = second.match(/\d+/g)?.map(Number) ?? [];
    if (firstNumbers[1] !== 0) throw new Error(`first run reused ${firstNumbers[1]}`);
    if (secondNumbers[0] !== 0) throw new Error(`second run created ${secondNumbers[0]}`);
  });
  mark("4. Predictive inventory — BO-01", "reorders created, rerun created none");

  // ------------------------------------------------------------------ step 5
  await guard("5. pricing run", async () => {
    await page.goto(`${UI}/backoffice/pricing`, { waitUntil: "load" });
    await settle(page);
    await page.locator(".inventory-run-button").click();
    await page.waitForSelector('p[data-tone="success"]', { timeout: 60000 });
    const message = await page.locator('p[data-tone="success"]').innerText();
    const numbers = message.match(/\d+/g)?.map(Number) ?? [];
    if (!numbers[0]) throw new Error(`no prices updated: ${message}`);
    await shot(page, "14-pricing-run", message);
  });
  mark("5a. Dynamic pricing run — BO-02", "bounded changes + audit trail");

  await guard("5b. pricing propagation", async () => {
    await page.goto(`${UI}/products/${PRODUCT}`, { waitUntil: "load" });
    await settle(page);
    const product = await api(`/v1/products/${PRODUCT}`);
    const priceText = await page.locator(".price-block").innerText();
    const digits = priceText.replace(/[^\d.]/g, "");
    if (!digits.includes(product.price.amount.split(".")[0]))
      throw new Error(`storefront price ${digits} != ${product.price.amount}`);
    await shot(page, "15-storefront-price", product.price.amount);

    await page.goto(`${UI}/orders/${confirmedOrder.id}`, { waitUntil: "load" });
    await settle(page);
    const order = await api(`/v1/orders/${confirmedOrder.id}`, { headers: CUSTOMER });
    if (order.items[0].unit_price !== confirmedOrder.unitPrice)
      throw new Error("order snapshot changed after repricing");
    await shot(page, "16-order-price-snapshot", `unit price ${order.items[0].unit_price}`);
  });
  mark("5b. Price propagation + snapshot — BO-02", "storefront updated, order unchanged");

  await guard("5c. pricing observation", async () => {
    await page.goto(`${UI}/backoffice/pricing`, { waitUntil: "load" });
    await settle(page);
    const before = await api("/v1/backoffice/pricing", { headers: OPERATOR });
    const beforeItem = before.items.find((item) => item.product_id === PRODUCT);
    await page.selectOption('select[name="product_id"]', PRODUCT);
    await page.fill('input[name="recorded_cost"]', beforeItem.observation.recorded_cost);
    await page.fill('input[name="competitor_cost"]', "20000");
    await page.fill('input[name="supply"]', "10");
    await page.fill('input[name="demand"]', "56");
    await page.locator(".pricing-form button[type=submit]").click();
    await page.waitForSelector('.pricing-form-actions p[data-tone="success"]', {
      timeout: 30000,
    });
    await shot(page, "17-pricing-import");

    await page.locator(".inventory-run-button").click();
    await page.waitForSelector('.inventory-run p[data-tone="success"]', { timeout: 60000 });
    const oldAmount = Number(beforeItem.current_amount);
    let newAmount = oldAmount;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const after = await api("/v1/backoffice/pricing", { headers: OPERATOR });
      const afterItem = after.items.find((item) => item.product_id === PRODUCT);
      newAmount = Number(afterItem.current_amount);
      if (newAmount !== oldAmount) break;
      await page.waitForTimeout(500);
    }
    if (newAmount <= oldAmount) throw new Error(`price did not rise: ${newAmount}`);
    if (newAmount > oldAmount * 1.2 + 0.01)
      throw new Error(`price exceeded cap: ${newAmount} vs ${oldAmount}`);
    await shot(page, "18-pricing-after-import", `${oldAmount} -> ${newAmount}`);
  });
  mark("5c. Observation import + bounded rerun — BO-02", "≤20% move applied");

  // ------------------------------------------------------------------ step 6
  await guard("6. segmentation", async () => {
    await page.goto(`${UI}/backoffice/segments`, { waitUntil: "load" });
    await settle(page);
    await page.locator(".inventory-run-button").click();
    await page.waitForSelector('p[data-tone="success"]', { timeout: 60000 });
    const message = await page.locator('p[data-tone="success"]').innerText();
    const numbers = message.match(/\d+/g)?.map(Number) ?? [];
    if (numbers[0] !== 38) throw new Error(`classified ${numbers[0]}`);
    if (numbers[1] !== 2) throw new Error(`insufficient ${numbers[1]}`);
    await shot(page, "19-segments", message);

    const cards = page.locator(".segment-card");
    if ((await cards.count()) !== 6) throw new Error("segment cards missing");
    const atRisk = page.locator('.segment-card[href*="at_risk"]').first();
    if (await atRisk.count()) {
      await atRisk.click();
      await page.waitForURL(/segment=at_risk/);
      await settle(page);
      await shot(page, "20-segments-filtered");
    }
    const csv = await fetch(`${API}/v1/backoffice/segments/export?segment=at_risk`, {
      headers: OPERATOR,
    });
    if (!csv.ok) throw new Error(`CSV export ${csv.status}`);
    const text = await csv.text();
    if (!text.startsWith("customer_id,")) throw new Error("CSV header mismatch");
  });
  mark("6. RFM segmentation — BO-03", "38 classified / 2 insufficient, CSV");

  // ------------------------------------------------------------------ step 7
  await guard("7. analytics", async () => {
    await page.goto(`${UI}/backoffice/analytics`, { waitUntil: "load" });
    await settle(page);
    await page.waitForSelector(".analytics-kpis dd", { timeout: 30000 });
    await page.waitForFunction(
      () => document.querySelectorAll(".analytics-recon tbody tr").length > 0,
      null,
      { timeout: 30000 },
    );
    const report = await api(
      `/v1/backoffice/analytics?from=${new Date(Date.now() - 89 * 864e5).toISOString().slice(0, 10)}&to=${new Date().toISOString().slice(0, 10)}`,
      { headers: OPERATOR },
    );
    if (!report.reconciliation.every((check) => check.matches))
      throw new Error("unfiltered reconciliation mismatch");
    await shot(page, "21-analytics");

    await page.selectOption('select[name="category"]', "phones");
    await page.locator('.analytics-filters button[type="submit"]').click();
    await page.waitForURL(/category=phones/);
    await settle(page);
    await page.waitForSelector(".analytics-kpis dd", { timeout: 30000 });
    await page.waitForFunction(
      () => document.querySelectorAll(".analytics-recon tbody tr").length > 0,
      null,
      { timeout: 30000 },
    );
    const filtered = await api(
      `/v1/backoffice/analytics?from=${report.scope.date_from}&to=${report.scope.date_to}&category=phones`,
      { headers: OPERATOR },
    );
    if (!filtered.reconciliation.every((check) => check.matches))
      throw new Error("filtered reconciliation mismatch");
    if (filtered.behaviour.product_views > report.behaviour.product_views)
      throw new Error("category filter did not reduce views");
    await shot(page, "22-analytics-phones");
  });
  mark("7. BI dashboards — BI-01", "filters recompute, reconciliation matches");

  // ------------------------------------------------------------------ parity
  await guard("8. English parity", async () => {
    const en = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce",
      locale: "en-GB",
    });
    await en.addCookies([
      { name: "smart_ecommerce_locale", value: "en", url: UI },
      ...SESSION_COOKIES,
    ]);
    const enPage = await en.newPage();
    await enPage.goto(`${UI}/`, { waitUntil: "load" });
    await enPage.waitForTimeout(200);
    const lang = await enPage.evaluate(() => ({
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
    }));
    if (lang.lang !== "en" || lang.dir !== "ltr") throw new Error(JSON.stringify(lang));
    await shot(enPage, "23-en-catalog");
    await enPage.goto(`${UI}/backoffice/analytics`, { waitUntil: "load" });
    await enPage.waitForSelector(".analytics-kpis dd", { timeout: 30000 });
    await enPage.waitForFunction(
      () => document.querySelectorAll(".analytics-recon tbody tr").length > 0,
      null,
      { timeout: 30000 },
    );
    await shot(enPage, "24-en-analytics");
    await en.close();
  });
  mark("8. English LTR parity", "lang=en dir=ltr");

  // ------------------------------------------------------------------ states
  await guard("9. honest states", async () => {
    const missing = await page.goto(`${UI}/products/99999999-0000-4000-8000-000000000000`, {
      waitUntil: "load",
    });
    if (missing?.status() !== 404) throw new Error(`missing product ${missing?.status()}`);
    await shot(page, "25-missing-product");

    await page.goto(`${UI}/assistant`, { waitUntil: "load" });
    await settle(page);
    await shot(page, "26-assistant");
  });
  mark("9. Failure states", "missing product 404, assistant provider state");

  // ------------------------------------------------------------------ backend
  await guard("10. backend evidence", async () => {
    const inventory = await api("/v1/backoffice/inventory", { headers: OPERATOR });
    if (!inventory.items?.length) throw new Error("inventory evidence missing");
    const model = await api("/v1/backoffice/risk/model", { headers: OPERATOR });
    if (Number(model.metrics.recall) < 0.8) throw new Error("fraud recall below target");
  });
  mark("10. Evidence check", "inventory + model evidence persisted");
} finally {
  await browser.close();
}

const total = log.reduce((sum, entry) => sum + entry.seconds, 0);
const summary = {
  totalSeconds: Number(total.toFixed(1)),
  steps: log,
  drift,
  screenshots,
  consoleErrors: [...new Set(consoleErrors)].slice(0, 20),
};
await writeFile("/tmp/opencode/rehearsal-result.json", JSON.stringify(summary, null, 2));
console.log(`\nTOTAL ${total.toFixed(1)}s, ${drift.length} drift, ${screenshots.length} screenshots, ${summary.consoleErrors.length} console errors`);
if (drift.length) for (const entry of drift) console.log(` - ${entry.step}: ${entry.error}`);
if (summary.consoleErrors.length) for (const entry of summary.consoleErrors) console.log(` ! console: ${entry}`);
process.exit(drift.length ? 1 : 0);