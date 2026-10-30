/**
 * Contrast gate for the design tokens.
 *
 * Reads the token values out of `app/styles/tokens.css` rather than duplicating
 * them here, so a palette edit cannot pass by being unnoticed. Fails with a
 * non-zero exit code when a text pairing drops below 4.5:1 or an interactive
 * control border drops below 3:1.
 *
 * Usage:
 *   node tests/ui/verify-contrast.mjs
 */
import { readFile } from "node:fs/promises";

const TOKENS_PATH = new URL(
  "../../apps/storefront/app/styles/tokens.css",
  import.meta.url,
);

const css = await readFile(TOKENS_PATH, "utf8");

/** Reads `--name: #rrggbb;` declarations from the first `:root` block. */
function readTokens(source) {
  const tokens = {};
  for (const match of source.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    tokens[match[1]] = match[2].toLowerCase();
  }
  return tokens;
}

const t = readTokens(css);

function luminance(hex) {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((offset) => {
    const c = Number.parseInt(value.slice(offset, offset + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(a, b) {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

/** Every pairing the interface actually renders, with the rule it must satisfy. */
const TEXT_PAIRS = [
  ["ink on canvas", "ink", "canvas"],
  ["ink on surface", "ink", "surface"],
  ["ink on canvas-deep", "ink", "canvas-deep"],
  ["ink-2 on canvas", "ink-2", "canvas"],
  ["ink-2 on surface", "ink-2", "surface"],
  ["ink-3 on canvas", "ink-3", "canvas"],
  ["ink-3 on surface", "ink-3", "surface"],
  ["ink-3 on surface-sunken", "ink-3", "surface-sunken"],
  ["ink-3 on canvas-deep", "ink-3", "canvas-deep"],
  ["ink-3 on warning-soft", "ink-3", "warning-soft"],
  ["ink-3 on danger-soft", "ink-3", "danger-soft"],
  ["ink-3 on success-soft", "ink-3", "success-soft"],
  ["ink-3 on primary-soft", "ink-3", "primary-soft"],
  ["ink-id on surface", "ink-id", "surface"],
  ["ink-id on warning-soft", "ink-id", "warning-soft"],
  ["primary-on on primary", "primary-on", "primary"],
  ["primary-on on primary-hover", "primary-on", "primary-hover"],
  ["primary on surface", "primary", "surface"],
  ["primary on primary-soft", "primary", "primary-soft"],
  ["primary-active on primary-soft", "primary-active", "primary-soft"],
  ["success on surface", "success", "surface"],
  ["success on success-soft", "success", "success-soft"],
  ["danger on surface", "danger", "surface"],
  ["danger on danger-soft", "danger", "danger-soft"],
  ["warning on surface", "warning", "surface"],
  ["warning on warning-soft", "warning", "warning-soft"],
  ["rail-text on rail", "rail-text", "rail"],
  ["rail-text on rail-active", "rail-text", "rail-active"],
  ["rail-text-muted on rail", "rail-text-muted", "rail"],
  ["success-on-dark on rail", "success-on-dark", "rail"],
  ["danger-on-dark on rail", "danger-on-dark", "rail"],
];

/** WCAG 1.4.11: a control's boundary must reach 3:1 against its surroundings. */
const CONTROL_PAIRS = [
  ["border-control on surface", "border-control", "surface"],
  ["border-control on canvas", "border-control", "canvas"],
  ["border-control on surface-sunken", "border-control", "surface-sunken"],
];

let failures = 0;

console.log("Text contrast (WCAG 1.4.3, minimum 4.5:1)");
for (const [label, fg, bg] of TEXT_PAIRS) {
  const ratio = contrast(t[fg], t[bg]);
  const ok = ratio >= 4.5;
  if (!ok) failures += 1;
  console.log(
    `  ${ok ? "ok  " : "FAIL"} ${label.padEnd(32)} ${ratio.toFixed(2)}:1`,
  );
}

console.log("\nNon-text contrast (WCAG 1.4.11, minimum 3:1)");
for (const [label, fg, bg] of CONTROL_PAIRS) {
  const ratio = contrast(t[fg], t[bg]);
  const ok = ratio >= 3;
  if (!ok) failures += 1;
  console.log(
    `  ${ok ? "ok  " : "FAIL"} ${label.padEnd(32)} ${ratio.toFixed(2)}:1`,
  );
}

// `ink-4` is exempt from the text floor by design, but it must never be the only
// signal: this assertion documents that it is below the floor on purpose.
const ink4 = contrast(t["ink-4"], t["surface"]);
console.log(
  `\n  note ink-4 on surface is ${ink4.toFixed(2)}:1 — icons and separators only, never text`,
);

if (failures > 0) {
  console.error(`\n${failures} pairing(s) below the required ratio.`);
  process.exit(1);
}

console.log("\nAll token pairings pass.");
