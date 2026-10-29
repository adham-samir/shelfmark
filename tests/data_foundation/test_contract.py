"""Validate the design contract, including decimal precision and public data boundaries."""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / "docs/api/catalog.openapi.json").read_text())
PLATFORM_SPEC = json.loads((ROOT / "docs/api/platform.openapi.json").read_text())


def validator(name):
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": SPEC["components"]},
        format_checker=FormatChecker(),
    )


class CatalogContractTests(unittest.TestCase):
    def test_openapi_structure_and_references(self):
        validate(SPEC)
        validate(PLATFORM_SPEC)

    def test_platform_contract_covers_stage_two_boundaries(self):
        paths = PLATFORM_SPEC["paths"]
        expected = {
            "/v1/events/browsing",
            "/v1/recommendations",
            "/v1/search/image",
            "/v1/search/voice",
            "/v1/assistant/messages",
            "/v1/cart",
            "/v1/cart/items",
            "/v1/checkout",
            "/v1/orders/{order_id}",
            "/v1/orders/{order_id}/shipment",
            "/v1/orders/{order_id}/cancel",
            "/v1/orders/{order_id}/reorder",
            "/v1/backoffice/inventory",
            "/v1/backoffice/reorders/run",
            "/v1/backoffice/pricing",
            "/v1/backoffice/pricing/run",
            "/v1/backoffice/pricing/observations",
            "/v1/backoffice/segments",
            "/v1/backoffice/segments/run",
            "/v1/backoffice/segments/export",
            "/v1/backoffice/risk",
            "/v1/backoffice/risk/model",
            "/v1/backoffice/risk/{assessment_id}/decision",
            "/v1/backoffice/analytics",
            "/v1/backoffice/orders",
            "/v1/backoffice/orders/{order_id}",
            "/v1/backoffice/orders/{order_id}/shipment",
            "/v1/backoffice/orders/{order_id}/cancel",
            "/v1/backoffice/orders/{order_id}/refund",
            "/v1/backoffice/inventory/{product_id}/adjustments",
            "/v1/auth/register",
            "/v1/auth/login",
            "/v1/auth/logout",
            "/v1/auth/me",
            "/v1/account",
            "/v1/account/password",
            "/v1/addresses",
            "/v1/addresses/{address_id}",
            "/v1/orders",
        }
        self.assertEqual(set(paths), expected)
        for path in (
            "/v1/auth/logout",
            "/v1/auth/me",
            "/v1/account",
            "/v1/account/password",
            "/v1/addresses",
            "/v1/addresses/{address_id}",
            "/v1/orders",
        ):
            for operation in paths[path].values():
                self.assertIn({"bearerAuth": []}, operation["security"])
        self.assertEqual(
            paths["/v1/auth/login"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/LoginInput",
        )
        risk_operation = paths["/v1/backoffice/risk"]["get"]
        risk_model_operation = paths["/v1/backoffice/risk/model"]["get"]
        self.assertIn({"bearerAuth": []}, risk_operation["security"])
        self.assertEqual(risk_operation["x-required-scopes"], ["risk:review"])
        self.assertIn({"bearerAuth": []}, risk_model_operation["security"])
        self.assertEqual(risk_model_operation["x-required-scopes"], ["risk:review"])
        self.assertEqual(
            risk_model_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/FraudModelSummary",
        )
        queue_properties = PLATFORM_SPEC["components"]["schemas"]["ReviewQueueItem"]["properties"]
        self.assertIn("model_version", queue_properties)
        self.assertIn("reasons", queue_properties)
        inventory_operation = paths["/v1/backoffice/inventory"]["get"]
        reorder_operation = paths["/v1/backoffice/reorders/run"]["post"]
        self.assertEqual(inventory_operation["x-required-scopes"], ["inventory:write"])
        self.assertEqual(reorder_operation["x-required-scopes"], ["inventory:write"])
        self.assertEqual(
            inventory_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/InventoryPlanningResponse",
        )
        self.assertEqual(
            reorder_operation["responses"]["202"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ReorderRunResult",
        )
        pricing_overview = paths["/v1/backoffice/pricing"]["get"]
        pricing_run = paths["/v1/backoffice/pricing/run"]["post"]
        pricing_import = paths["/v1/backoffice/pricing/observations"]["post"]
        for operation in (pricing_overview, pricing_run, pricing_import):
            self.assertEqual(operation["x-required-scopes"], ["pricing:write"])
            self.assertIn({"bearerAuth": []}, operation["security"])
        self.assertEqual(
            pricing_overview["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/PricingOverviewResponse",
        )
        self.assertEqual(
            pricing_run["responses"]["202"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/PricingRunResult",
        )
        self.assertEqual(
            pricing_import["responses"]["202"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/PricingObservationResult",
        )
        segments = paths["/v1/backoffice/segments"]["get"]
        segments_run = paths["/v1/backoffice/segments/run"]["post"]
        segments_export = paths["/v1/backoffice/segments/export"]["get"]
        for operation in (segments, segments_run, segments_export):
            self.assertEqual(operation["x-required-scopes"], ["segments:read"])
            self.assertIn({"bearerAuth": []}, operation["security"])
        self.assertEqual(
            segments["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/SegmentationResponse",
        )
        self.assertEqual(
            segments_run["responses"]["202"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/SegmentationRunResult",
        )
        self.assertIn("text/csv", segments_export["responses"]["200"]["content"])
        analytics = paths["/v1/backoffice/analytics"]["get"]
        self.assertEqual(analytics["x-required-scopes"], ["analytics:read"])
        self.assertIn({"bearerAuth": []}, analytics["security"])
        self.assertEqual(
            analytics["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/AnalyticsResponse",
        )
        self.assertEqual(
            [parameter["name"] for parameter in analytics["parameters"]],
            ["from", "to", "category"],
        )

    def test_product_example_and_empty_page(self):
        validator("Product").validate(SPEC["components"]["schemas"]["Product"]["example"])
        page = SPEC["paths"]["/v1/products"]["get"]["responses"]["200"]["content"]["application/json"]["examples"]["empty"]["value"]
        validator("ProductPage").validate(page)

    def test_price_rejects_float_nonfinite_negative_and_excess_precision(self):
        base = {"currency": "XXX", "updated_at": "2026-10-27T00:00:00Z"}
        for amount in [12.5, "NaN", "Infinity", "-0.01", "1.0000001", "100000000000000", "01.00"]:
            with self.subTest(amount=amount):
                self.assertFalse(validator("Price").is_valid({**base, "amount": amount}))
        validator("Price").validate({**base, "amount": "99999999999999.999999"})
        validator("Price").validate({**base, "amount": "0"})

    def test_public_product_rejects_internal_fields_and_bad_identifiers(self):
        product = SPEC["components"]["schemas"]["Product"]["example"]
        for key, value in [("provenance", {"kind": "synthetic"}), ("on_hand", 4)]:
            with self.subTest(key=key):
                self.assertFalse(validator("Product").is_valid({**product, key: value}))
        changed = copy.deepcopy(product)
        changed["product_id"] = "ObjectId-from-another-store"
        self.assertFalse(validator("Product").is_valid(changed))
        changed = copy.deepcopy(product)
        changed["images"] = [{"uri": "javascript:alert(1)", "alt": "Invalid image"}]
        self.assertFalse(validator("Product").is_valid(changed))

    def test_pagination_and_error_envelope(self):
        page = {"items": [], "total": 0, "limit": 20, "offset": 0}
        for key, value in [("limit", 0), ("limit", 101), ("offset", -1), ("total", -1)]:
            with self.subTest(key=key, value=value):
                self.assertFalse(validator("ProductPage").is_valid({**page, key: value}))
        error = {"error": {"code": "dependency_unavailable", "message": "Catalog unavailable.", "request_id": "10000000-0000-4000-8000-000000000002"}}
        validator("Error").validate(error)
        self.assertFalse(validator("Error").is_valid({"detail": "Unnormalized framework error"}))
