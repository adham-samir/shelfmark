/**
 * Browser selection for the verification harnesses.
 *
 * The default is the system Chromium, because that is what the local stack and
 * the CI image provide. `BROWSER=firefox|webkit` drives the Playwright-bundled
 * engine instead. A system Firefox is not a substitute: Playwright patches the
 * browsers it ships, and only those speak the protocol this harness uses.
 *
 * Install them once with:
 *   node node_modules/playwright-core/cli.js install firefox webkit
 */
import { chromium, firefox, webkit } from "playwright-core";

const ENGINES = { chromium, firefox, webkit };

export const BROWSER = process.env.BROWSER ?? "chromium";

/** A capture label or report title that names the engine when it is not the default. */
export function engineLabel(base) {
  return BROWSER === "chromium" ? base : `${base}-${BROWSER}`;
}

export async function launchBrowser() {
  const engine = ENGINES[BROWSER];
  if (!engine) {
    throw new Error(
      `unknown BROWSER "${BROWSER}"; expected chromium, firefox or webkit`,
    );
  }
  if (BROWSER === "chromium") {
    return engine.launch({
      executablePath:
        process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?? "/usr/bin/chromium",
      args: ["--no-sandbox"],
    });
  }
  return engine.launch();
}
