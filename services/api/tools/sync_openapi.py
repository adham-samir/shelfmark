"""Synchronize implemented smart-storefront operations into the platform contract."""

import json
from pathlib import Path

from smart_ecommerce_api.main import app


ROOT = Path(__file__).resolve().parents[3]
PLATFORM_PATH = ROOT / "docs/api/platform.openapi.json"
IMPLEMENTED_PATHS = {
    "/v1/assistant/messages",
    "/v1/search/image",
    "/v1/search/voice",
    "/v1/backoffice/inventory",
    "/v1/backoffice/reorders/run",
}


def main() -> None:
    platform = json.loads(PLATFORM_PATH.read_text(encoding="utf-8"))
    generated = app.openapi()
    for path in IMPLEMENTED_PATHS:
        platform["paths"][path] = generated["paths"][path]
    platform["paths"]["/v1/search/image"]["post"]["security"] = []
    platform["paths"]["/v1/search/voice"]["post"]["security"] = []
    for path, method in [
        ("/v1/backoffice/inventory", "get"),
        ("/v1/backoffice/reorders/run", "post"),
    ]:
        operation = platform["paths"][path][method]
        operation["security"] = [{"bearerAuth": []}]
        operation["x-required-scopes"] = ["inventory:write"]
    platform["components"]["schemas"].update(generated["components"]["schemas"])
    platform["info"]["version"] = "0.4.0"
    platform["info"]["description"] = (
        "Platform contracts. Catalog, interaction capture, recommendations, assistant, "
        "image/voice search, cart, checkout, owned order/shipment reads, risk review, "
        "and BO-01 inventory forecasting/reordering are implemented; remaining "
        "back-office operations are design-only."
    )
    PLATFORM_PATH.write_text(
        json.dumps(platform, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
