from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from smart_ecommerce_api.auth import Principal
from smart_ecommerce_api.catalog import (
    CatalogService,
    OperationalProduct,
    PostgresOperationalCatalog,
)
from smart_ecommerce_api.errors import (
    DependencyUnavailable,
    ProductNotFound,
    Unauthorized,
)
from smart_ecommerce_api.commerce_models import (
    Cart,
    InventoryAdjustmentResult,
    OperatorCustomer,
    OperatorOrderDetail,
    OperatorOrderList,
    OperatorOrderSummary,
    OperatorShipping,
    OrderAdjustmentResult,
    OrderItem,
    OrderList,
    OrderStatus,
    OrderSummary,
    ReviewDecisionResult,
    ReviewQueueItem,
    Shipment,
    ShipmentEvent,
)
from smart_ecommerce_api.analytics import (
    AnalyticsResponse,
    AnalyticsScope,
    BehaviourMetrics,
    DailyPoint,
    FinancialMetrics,
    ReconciliationCheck,
)
from smart_ecommerce_api.fraud import FraudModelSummary
from smart_ecommerce_api.identity import (
    AccountProfile,
    AccountView,
    AuthSession,
    LoginInput,
    RegisterInput,
)
from smart_ecommerce_api.main import create_app
from smart_ecommerce_api.models import Availability, Price, Product, ProductPage
from smart_ecommerce_api.forecasting import (
    InventoryPlanningResponse,
    InventoryPolicy,
    ReorderRunResult,
)
from smart_ecommerce_api.analytics import (
    AnalyticsResponse,
    AnalyticsScope,
    BehaviourMetrics,
    DailyPoint,
    FinancialMetrics,
    ReconciliationCheck,
)
from smart_ecommerce_api.fraud import FraudModelSummary
from smart_ecommerce_api.pricing import (
    PricingObservationResult,
    PricingOverviewResponse,
    PricingPolicy,
    PricingRunResult,
    PricingSeason,
)
from smart_ecommerce_api.segmentation import (
    SEGMENTS,
    CustomerSegment,
    RfmPolicy,
    SegmentCount,
    SegmentationResponse,
    SegmentationRunResult,
)


PRODUCT_ID = UUID("10000000-0000-4000-8000-000000000001")
REQUEST_ID = "90000000-0000-4000-8000-000000000009"
NOW = datetime(2026, 10, 27, tzinfo=UTC)


def product() -> Product:
    return Product(
        product_id=PRODUCT_ID,
        name="X1 Synthetic Phone",
        description="Synthetic fixture",
        categories=["phones"],
        attributes={"storage": "128 GB"},
        images=[],
        price=Price(amount="8900", currency="EGP", updated_at=NOW),
        availability=Availability(status="in_stock", updated_at=NOW),
    )


class FakeService:
    failure: Exception | None = None

    def check_dependencies(self) -> None:
        if self.failure:
            raise self.failure

    def list_products(
        self, *, query, category, limit, offset, filters=None, sort="relevance",
        availability=None, price_min=None, price_max=None,
    ) -> ProductPage:
        if self.failure:
            raise self.failure
        return ProductPage(items=[product()], total=1, limit=limit, offset=offset)

    def get_product(self, product_id: UUID) -> Product:
        if self.failure:
            raise self.failure
        if product_id != PRODUCT_ID:
            raise ProductNotFound()
        return product()

    def facets(self, *, query, category, filters, availability=None, price_min=None, price_max=None):
        from smart_ecommerce_api.models import CatalogFacets, Facet, FacetOption

        return CatalogFacets(
            total=1,
            facets=[
                Facet(key="storage", options=[FacetOption(value="128 GB", count=1)])
            ],
        )


class FakeAuthenticator:
    def authenticate(self, token: str) -> Principal:
        if token == "customer-token":
            return Principal(
                principal_id=UUID("30000000-0000-4000-8000-000000000001"),
                account_type="customer",
                customer_id=UUID("20000000-0000-4000-8000-000000000001"),
                scopes=frozenset(),
            )
        return Principal(
            principal_id=UUID("30000000-0000-4000-8000-000000000002"),
            account_type="backoffice",
            customer_id=None,
            scopes=frozenset(
                {
                    "orders:read",
                    "orders:write",
                    "risk:review",
                    "inventory:write",
                    "pricing:write",
                    "segments:read",
                    "analytics:read",
                }
            ),
        )


class FakeCommerce:
    def __init__(self) -> None:
        self.recorded_event = None

    def get_cart(self, customer_id: UUID) -> Cart:
        return Cart(
            cart_id=UUID("40000000-0000-4000-8000-000000000001"),
            items=[],
            subtotal="0",
        )

    def set_cart_item(self, customer_id: UUID, product_id: UUID, quantity: int) -> Cart:
        return self.get_cart(customer_id)

    def checkout(
        self, customer_id: UUID, payment_token: str, idempotency_key: str, shipping
    ) -> OrderStatus:
        return OrderStatus(
            order_id=UUID("70000000-0000-4000-8000-000000000001"),
            status="confirmed",
        )

    def list_orders(self, customer_id: UUID, *, limit: int = 20, offset: int = 0) -> OrderList:
        items = [
            OrderSummary(
                order_id=UUID("70000000-0000-4000-8000-000000000001"),
                status="confirmed",
                currency="EGP",
                subtotal="8900",
                item_count=1,
                created_at=NOW,
            )
        ]
        return OrderList(items=items, total=1, limit=limit, offset=offset)

    def record_event(self, customer_id: UUID, **event) -> None:
        self.recorded_event = (customer_id, event)

    def list_risk_reviews(self) -> list[ReviewQueueItem]:
        return [
            ReviewQueueItem(
                assessment_id=UUID("93000000-0000-4000-8000-000000000001"),
                order_id=UUID("70000000-0000-4000-8000-000000000001"),
                customer_id=UUID("20000000-0000-4000-8000-000000000001"),
                score="0.9120000",
                outcome="review",
                subtotal="8900",
                assessed_at=NOW,
                model_version="logistic-regression-fraud-v1",
                reasons=["model_score_at_or_above_threshold"],
            )
        ]

    def decide_review(self, reviewer_principal_id: UUID, assessment_id: UUID, decision: str):
        return ReviewDecisionResult(
            assessment_id=assessment_id,
            order_id=UUID("70000000-0000-4000-8000-000000000001"),
            status="confirmed" if decision == "allow" else "cancelled",
        )

    def operator_list_orders(
        self, *, status=None, limit: int = 20, offset: int = 0
    ) -> OperatorOrderList:
        items = [
            OperatorOrderSummary(
                order_id=UUID("70000000-0000-4000-8000-000000000001"),
                status="review",
                currency="EGP",
                subtotal="8900",
                refund_total="0",
                item_count=1,
                created_at=NOW,
                customer=OperatorCustomer(
                    customer_id=UUID("20000000-0000-4000-8000-000000000001"),
                    email="customer@example.invalid",
                    display_name="Synthetic Customer",
                ),
            )
        ]
        if status is not None:
            items = [item for item in items if item.status == status]
        return OperatorOrderList(
            items=items, total=len(items), limit=limit, offset=offset, status=status
        )

    def operator_get_order(self, order_id: UUID) -> OperatorOrderDetail:
        return OperatorOrderDetail(
            order_id=order_id,
            status="review",
            currency="EGP",
            subtotal="8900",
            refund_total="0",
            created_at=NOW,
            customer=OperatorCustomer(
                customer_id=UUID("20000000-0000-4000-8000-000000000001"),
                email="customer@example.invalid",
                display_name="Synthetic Customer",
            ),
            shipping=OperatorShipping(
                recipient_name="Synthetic Customer",
                phone="+201000000001",
                city="Cairo",
                address_line="1 Synthetic Street",
            ),
            items=[
                OrderItem(
                    product_id=PRODUCT_ID,
                    product_name="X1 Phone",
                    quantity=1,
                    unit_price="8900",
                    line_total="8900",
                )
            ],
            shipment=None,
        )

    def operator_transition_shipment(self, order_id: UUID, target: str, actor_principal_id: UUID) -> Shipment:
        return Shipment(
            shipment_id=UUID("80000000-0000-4000-8000-000000000001"),
            status=target,
            updated_at=NOW,
            events=[
                ShipmentEvent(
                    status=target,
                    description_ar="تم تحديث الشحنة",
                    description_en="Shipment updated",
                    occurred_at=NOW,
                )
            ],
        )

    def operator_cancel_order(self, order_id: UUID, reason: str, actor_principal_id: UUID) -> OrderAdjustmentResult:
        return OrderAdjustmentResult(
            order_id=order_id,
            status="cancelled",
            refund_total="0",
            adjustment_id=UUID("90000000-0000-4000-8000-000000000001"),
            kind="cancellation",
            amount="0",
            created_at=NOW,
        )

    def operator_refund_order(self, order_id: UUID, amount: str, reason: str, actor_principal_id: UUID) -> OrderAdjustmentResult:
        return OrderAdjustmentResult(
            order_id=order_id,
            status="refunded",
            refund_total=amount,
            adjustment_id=UUID("90000000-0000-4000-8000-000000000002"),
            kind="refund",
            amount=amount,
            created_at=NOW,
        )

    def operator_adjust_inventory(self, product_id: UUID, quantity_delta: int, reason: str, actor_principal_id: UUID) -> InventoryAdjustmentResult:
        return InventoryAdjustmentResult(
            product_id=product_id,
            on_hand=10 + quantity_delta,
            reserved=2,
            available=8 + quantity_delta,
            movement_id=UUID("90000000-0000-4000-8000-000000000003"),
            occurred_at=NOW,
        )


class FakeInventory:
    def planning(self) -> InventoryPlanningResponse:
        return InventoryPlanningResponse(
            generated_at=NOW,
            policy=InventoryPolicy(),
            items=[],
        )

    def run(self) -> ReorderRunResult:
        return ReorderRunResult(
            run_date=NOW.date(),
            model_version="random-forest-lag-calendar-v1",
            forecasts_generated=0,
            reorders_created=0,
            reorders_reused=0,
            adequate_stock=0,
            insufficient_history=0,
            items=[],
        )


class FakePricing:
    def overview(self) -> PricingOverviewResponse:
        return PricingOverviewResponse(
            generated_at=NOW,
            as_of=NOW.date(),
            season=PricingSeason(
                season_id="standard",
                label_en="Standard demand",
                label_ar="طلب اعتيادي",
                price_multiplier="1.00",
            ),
            policy=PricingPolicy(),
            items=[],
            recent_changes=[],
        )

    def run(self, *, product_ids=None) -> PricingRunResult:
        return PricingRunResult(
            run_date=NOW.date(),
            policy_version="dec-009-v1",
            season_id="standard",
            evaluated=0,
            updated=0,
            unchanged=0,
            missing_input=0,
            stale_input=0,
            constraint_blocked=0,
            already_applied=0,
            conflict=0,
            items=[],
        )

    def record_observation(self, observation) -> PricingObservationResult:
        from smart_ecommerce_api.pricing import (
            PricingObservationInput,
        )

        assert isinstance(observation, PricingObservationInput)
        return PricingObservationResult(
            observation_id=UUID("60000000-0000-4000-8000-000000000001"),
            product_id=observation.product_id,
            observed_at=NOW,
            season_id="standard",
            provenance=observation.provenance,
        )


class FakeAnalytics:
    def report(self, *, date_from, date_to, category=None) -> AnalyticsResponse:
        return AnalyticsResponse(
            generated_at=NOW,
            scope=AnalyticsScope(
                date_from=date_from,
                date_to=date_to,
                category=category,
                category_product_count=1 if category else 0,
            ),
            behaviour=BehaviourMetrics(
                product_views=120,
                sessions=30,
                add_to_carts=9,
                created_orders=6,
                orders_per_session="0.2",
                unfulfilled_orders=1,
            ),
            financial=FinancialMetrics(
                order_count=6,
                gross_sales="60000",
                refunds="5000",
                net_sales="55000",
                average_order_value="9166.67",
            ),
            top_products=[],
            daily=[
                DailyPoint(
                    day=date_from,
                    views=12,
                    sessions=3,
                    orders=1,
                    net_sales="9000",
                )
            ],
            reconciliation=[
                ReconciliationCheck(
                    metric="gross_sales",
                    reported="60000",
                    recomputed="60000",
                    matches=True,
                    source="order_items.line_total",
                )
            ],
            no_events=False,
            no_orders=False,
            category_without_products=False,
        )


class FakeRiskModel:
    def summary(self) -> FraudModelSummary:
        return FraudModelSummary(
            model_version_id=UUID("6096db2d-031f-5a57-b7b5-1da2bd7924b3"),
            version_label="logistic-regression-fraud-v1",
            dataset_snapshot_id="fraud-synthetic-2026-10-27-v1",
            threshold="0.6985274317596127",
            feature_names=["amount_ratio"],
            metrics={"recall": 0.833, "false_positive_rate": 0.078},
            limitations="Synthetic data only.",
            trained_at="2026-10-27T20:00:00+00:00",
        )


class FakeSegmentation:
    display_name = "Synthetic Customer"

    def _member(self) -> CustomerSegment:
        return CustomerSegment(
            customer_id=UUID("20000000-0000-4000-8000-000000000001"),
            email="customer@example.invalid",
            display_name=self.display_name,
            reference_date=date(2026, 10, 27),
            recency_days=3,
            frequency=9,
            monetary=Decimal("71234.5"),
            recency_score=5,
            frequency_score=5,
            monetary_score=5,
            segment="champions",
        )

    def overview(
        self, *, reference_date=None, segment=None, limit=50, offset=0
    ) -> SegmentationResponse:
        members = [] if segment == "loyal" else [self._member()]
        return SegmentationResponse(
            snapshot_available=True,
            reference_date=date(2026, 10, 27),
            observation_start=date(2025, 10, 28),
            generated_at=NOW,
            stale=False,
            policy=RfmPolicy(),
            cohort_size=1,
            insufficient_history=0,
            counts=[
                SegmentCount(
                    segment=name, customers=1 if name == "champions" else 0
                )
                for name in SEGMENTS
            ],
            members=members,
            total_members=len(members),
            limit=limit,
            offset=offset,
        )

    def run(self) -> SegmentationRunResult:
        return SegmentationRunResult(
            reference_date=date(2026, 10, 27),
            observation_start=date(2025, 10, 28),
            policy_version="dec-011-v1",
            classified=1,
            insufficient_history=0,
            eligible_orders=1,
            excluded_orders=0,
            cohort_size=1,
            counts=[
                SegmentCount(
                    segment=name, customers=1 if name == "champions" else 0
                )
                for name in SEGMENTS
            ],
        )

    def export_rows(self, *, reference_date=None, segment=None):
        if segment == "loyal":
            return []
        return [self._member()]



class FakeIdentity:
    """In-memory identity store used to exercise the route wiring."""

    def __init__(self) -> None:
        self.tokens: dict[str, Principal] = {}
        self.current_profile = AccountProfile(
            customer_id=UUID("20000000-0000-4000-8000-000000000001"),
            email="customer@example.invalid",
            display_name="Synthetic Customer",
            preferred_locale="ar",
            member_since=NOW,
            order_count=1,
        )
        self.customer = Principal(
            principal_id=UUID("30000000-0000-4000-8000-000000000001"),
            account_type="customer",
            customer_id=self.current_profile.customer_id,
            scopes=frozenset(),
        )
        self.operator = Principal(
            principal_id=UUID("30000000-0000-4000-8000-000000000002"),
            account_type="backoffice",
            customer_id=None,
            scopes=frozenset({"risk:review"}),
        )
        self.last_registration: RegisterInput | None = None

    def _issue(self, principal: Principal, surface: str) -> AuthSession:
        token = f"session-{len(self.tokens) + 1}"
        self.tokens[token] = principal
        return AuthSession(
            token=token,
            surface=surface,
            expires_at=datetime(2026, 11, 4, tzinfo=UTC),
            account=self.view(principal),
        )

    def authenticate(self, token: str) -> Principal:
        principal = self.tokens.get(token)
        if principal is None:
            raise Unauthorized()
        return principal

    def login(self, credentials: LoginInput) -> AuthSession:
        if credentials.surface == "operator":
            if (
                credentials.email != "operator@example.invalid"
                or credentials.password != "demo-operator-1"
            ):
                raise Unauthorized()
            return self._issue(self.operator, "operator")
        if (
            credentials.email != self.current_profile.email
            or credentials.password != "demo-customer-1"
        ):
            raise Unauthorized()
        return self._issue(self.customer, "customer")

    def register(self, registration: RegisterInput) -> AuthSession:
        self.last_registration = registration
        profile = self.current_profile.model_copy(
            update={
                "email": registration.email.lower(),
                "display_name": registration.display_name,
                "preferred_locale": registration.preferred_locale,
                "order_count": 0,
            }
        )
        principal = Principal(
            principal_id=self.customer.principal_id,
            account_type="customer",
            customer_id=profile.customer_id,
            scopes=frozenset(),
        )
        self.current_profile = profile
        return self._issue(principal, "customer")

    def revoke(self, token: str) -> None:
        self.tokens.pop(token, None)

    def view(self, principal: Principal) -> AccountView:
        return AccountView(
            principal_id=principal.principal_id,
            account_type=principal.account_type,
            customer_id=principal.customer_id,
            scopes=sorted(principal.scopes),
            profile=self.current_profile if principal.customer_id is not None else None,
        )

    def profile(self, customer_id: UUID) -> AccountProfile:
        return self.current_profile

    def update_profile(self, customer_id: UUID, update) -> AccountProfile:
        payload = self.current_profile.model_dump()
        if update.display_name is not None:
            payload["display_name"] = update.display_name
        if update.preferred_locale is not None:
            payload["preferred_locale"] = update.preferred_locale
        self.current_profile = AccountProfile(**payload)
        return self.current_profile


def client(
    service: FakeService | None = None,
    commerce: FakeCommerce | None = None,
    segmentation: FakeSegmentation | None = None,
    identity: FakeIdentity | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            service or FakeService(),
            commerce or FakeCommerce(),
            identity or FakeAuthenticator(),
            inventory_service=FakeInventory(),
            pricing_service=FakePricing(),
            segmentation_service=segmentation or FakeSegmentation(),
            analytics_service=FakeAnalytics(),
            risk_model=FakeRiskModel(),
            identity_store=identity,
        ),
        raise_server_exceptions=False,
    )


def test_liveness_and_readiness() -> None:
    api = client()
    assert api.get("/health/live").json() == {"status": "live"}
    assert api.get("/health/ready").json() == {"status": "ready"}


def test_catalog_page_and_detail_use_contract_shape() -> None:
    api = client()
    response = api.get("/v1/products?limit=10&offset=0")
    assert response.status_code == 200
    assert response.json()["items"][0]["price"]["amount"] == "8900"
    assert response.json()["items"][0]["product_id"] == str(PRODUCT_ID)
    assert api.get(f"/v1/products/{PRODUCT_ID}").status_code == 200


def test_public_errors_are_normalized_and_request_id_is_preserved() -> None:
    api = client()
    response = api.get(
        "/v1/products/not-a-uuid", headers={"x-request-id": REQUEST_ID}
    )
    assert response.status_code == 422
    assert response.headers["x-request-id"] == REQUEST_ID
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "The request is invalid.",
            "request_id": REQUEST_ID,
        }
    }


def test_missing_product_and_dependency_failure_are_distinct() -> None:
    api = client()
    missing = api.get("/v1/products/20000000-0000-4000-8000-000000000002")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "product_not_found"

    service = FakeService()
    service.failure = DependencyUnavailable()
    unavailable = client(service).get("/v1/products")
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "dependency_unavailable"


class FakeOperational:
    def __init__(self, records: list[OperationalProduct]) -> None:
        self.records = records

    def list_active(self) -> list[OperationalProduct]:
        return self.records

    def get_active(self, product_id: UUID) -> OperationalProduct | None:
        return next((record for record in self.records if record.product_id == product_id), None)

    def ping(self) -> None:
        return None


class FakeDescriptive:
    def __init__(self, records: dict[str, dict]) -> None:
        self.records = records

    def get_many(self, product_ids: list[UUID]) -> dict[str, dict]:
        return {str(key): self.records[str(key)] for key in product_ids if str(key) in self.records}

    def get_one(self, product_id: UUID) -> dict | None:
        return self.records.get(str(product_id))

    def ping(self) -> None:
        return None


def operational_record(
    product_id: UUID = PRODUCT_ID, amount: str = "8900.000000"
) -> OperationalProduct:
    return OperationalProduct(
        product_id=product_id,
        amount=Decimal(amount),
        currency="EGP",
        price_updated_at=NOW,
        available=10,
        inventory_updated_at=NOW,
    )


def descriptive_record(name: str = "X1 Synthetic Phone") -> dict:
    return {
        "_id": str(PRODUCT_ID),
        "name": name,
        "description": "Synthetic bilingual-ready smartphone fixture.",
        "categories": ["phones"],
        "attributes": {"storage": "128 GB"},
        "images": [],
    }


def test_catalog_service_filters_before_pagination_and_formats_decimal() -> None:
    service = CatalogService(
        FakeOperational([operational_record()]),
        FakeDescriptive({str(PRODUCT_ID): descriptive_record()}),
    )
    page = service.list_products(
        query="phone", category="phones", limit=20, offset=0
    )
    assert page.total == 1
    assert page.items[0].price.amount == "8900"
    assert service.list_products(
        query="laptop", category=None, limit=20, offset=0
    ).total == 0


def test_catalog_service_sorts_before_pagination() -> None:
    cheaper = UUID("10000000-0000-4000-8000-000000000002")
    service = CatalogService(
        FakeOperational([operational_record(PRODUCT_ID), operational_record(cheaper, "2400.000000")]),
        FakeDescriptive(
            {
                str(PRODUCT_ID): descriptive_record("X1 Synthetic Phone"),
                str(cheaper): {**descriptive_record("H1 Synthetic Headphones"), "_id": str(cheaper)},
            }
        ),
    )
    ascending = service.list_products(
        query=None, category=None, limit=20, offset=0, sort="price_asc"
    )
    assert [item.product_id for item in ascending.items] == [cheaper, PRODUCT_ID]
    descending = service.list_products(
        query=None, category=None, limit=20, offset=0, sort="price_desc"
    )
    assert [item.product_id for item in descending.items] == [PRODUCT_ID, cheaper]
    by_name = service.list_products(
        query=None, category=None, limit=20, offset=0, sort="name_asc"
    )
    assert [item.name for item in by_name.items] == [
        "H1 Synthetic Headphones",
        "X1 Synthetic Phone",
    ]
    unsorted_page = service.list_products(
        query=None, category=None, limit=1, offset=1, sort="price_asc"
    )
    assert unsorted_page.total == 2
    assert [item.product_id for item in unsorted_page.items] == [PRODUCT_ID]


def test_catalog_service_fails_closed_on_cross_store_gap() -> None:
    service = CatalogService(FakeOperational([operational_record()]), FakeDescriptive({}))
    try:
        service.list_products(query=None, category=None, limit=20, offset=0)
    except DependencyUnavailable as error:
        assert error.code == "dependency_unavailable"
    else:
        raise AssertionError("missing MongoDB counterpart must fail closed")


def test_operational_gateway_fails_closed_on_missing_price_or_stock() -> None:
    incomplete = {
        "product_id": PRODUCT_ID,
        "amount": None,
        "currency": None,
        "price_updated_at": None,
        "available": None,
        "inventory_updated_at": None,
    }
    try:
        PostgresOperationalCatalog._record(incomplete)
    except DependencyUnavailable as error:
        assert "price or inventory" in error.message
    else:
        raise AssertionError("incomplete operational data must fail closed")


def test_customer_routes_require_customer_identity() -> None:
    api = client()
    missing = api.get("/v1/cart")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "unauthorized"

    customer = api.get(
        "/v1/cart", headers={"authorization": "Bearer customer-token"}
    )
    assert customer.status_code == 200
    assert customer.json()["currency"] == "EGP"

    operator = api.get(
        "/v1/cart", headers={"authorization": "Bearer operator-token"}
    )
    assert operator.status_code == 403


def test_event_checkout_and_review_routes_apply_boundaries() -> None:
    commerce = FakeCommerce()
    api = client(commerce=commerce)
    customer_headers = {"authorization": "Bearer customer-token"}
    event = {
        "event_id": "91000000-0000-4000-8000-000000000001",
        "session_id": "92000000-0000-4000-8000-000000000001",
        "product_id": str(PRODUCT_ID),
        "event_type": "view",
        "occurred_at": "2026-10-27T00:00:00Z",
        "context": {"surface": "catalog"},
    }
    assert api.post("/v1/events/browsing", json=event, headers=customer_headers).status_code == 202
    assert commerce.recorded_event[1]["event_type"] == "view"

    checkout = api.post(
        "/v1/checkout",
        json={
            "payment_token": "tok_sandbox_safe-1",
            "idempotency_key": "checkout-test-key-0001",
            "shipping": {
                "recipient_name": "Synthetic Customer",
                "phone": "+201000000001",
                "city": "Cairo",
                "address_line": "12 Synthetic Street",
            },
        },
        headers=customer_headers,
    )
    assert checkout.status_code == 202
    assert checkout.json()["status"] == "confirmed"

    assessment_id = "93000000-0000-4000-8000-000000000001"
    denied = api.post(
        f"/v1/backoffice/risk/{assessment_id}/decision",
        json={"decision": "allow"},
        headers=customer_headers,
    )
    assert denied.status_code == 403
    allowed = api.post(
        f"/v1/backoffice/risk/{assessment_id}/decision",
        json={"decision": "allow"},
        headers={"authorization": "Bearer operator-token"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "confirmed"


def test_inventory_routes_require_capability_and_return_typed_results() -> None:
    api = client()
    assert api.get("/v1/backoffice/inventory").status_code == 401
    denied = api.get(
        "/v1/backoffice/inventory",
        headers={"authorization": "Bearer customer-token"},
    )
    assert denied.status_code == 403

    headers = {"authorization": "Bearer operator-token"}
    planning = api.get("/v1/backoffice/inventory", headers=headers)
    assert planning.status_code == 200
    assert planning.json()["policy"]["forecast_days"] == 14

    run = api.post("/v1/backoffice/reorders/run", headers=headers)
    assert run.status_code == 202
    assert run.json()["model_version"] == "random-forest-lag-calendar-v1"


def test_pricing_routes_require_capability_and_return_typed_results() -> None:
    api = client()
    assert api.get("/v1/backoffice/pricing").status_code == 401
    denied = api.get(
        "/v1/backoffice/pricing",
        headers={"authorization": "Bearer customer-token"},
    )
    assert denied.status_code == 403

    headers = {"authorization": "Bearer operator-token"}
    overview = api.get("/v1/backoffice/pricing", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["policy"]["max_change_ratio"] == "0.20"
    assert overview.json()["policy"]["minimum_margin_ratio"] == "0.05"
    assert overview.json()["season"]["season_id"] == "standard"

    run = api.post(
        "/v1/backoffice/pricing/run",
        headers=headers,
        json={"product_ids": [str(PRODUCT_ID)]},
    )
    assert run.status_code == 202
    assert run.json()["policy_version"] == "dec-009-v1"
    assert run.json()["evaluated"] == 0

    run_all = api.post("/v1/backoffice/pricing/run", headers=headers)
    assert run_all.status_code == 202
    assert run_all.json()["evaluated"] == 0

    observation = api.post(
        "/v1/backoffice/pricing/observations",
        headers=headers,
        json={
            "product_id": str(PRODUCT_ID),
            "recorded_cost": "6230",
            "supply": "10",
            "demand": "56",
            "competitor_cost": "6500",
        },
    )
    assert observation.status_code == 202
    assert observation.json()["provenance"] == "synthetic"
    assert observation.json()["season_id"] == "standard"

    invalid = api.post(
        "/v1/backoffice/pricing/observations",
        headers=headers,
        json={
            "product_id": str(PRODUCT_ID),
            "recorded_cost": "0",
            "supply": "10",
            "demand": "56",
            "competitor_cost": "6500",
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"



def test_segmentation_routes_require_capability_and_return_typed_results() -> None:
    api = client()
    assert api.get("/v1/backoffice/segments").status_code == 401
    denied = api.get(
        "/v1/backoffice/segments",
        headers={"authorization": "Bearer customer-token"},
    )
    assert denied.status_code == 403

    headers = {"authorization": "Bearer operator-token"}
    overview = api.get("/v1/backoffice/segments", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["policy"]["window_days"] == 365
    assert len(body["counts"]) == 6
    assert body["members"][0]["segment"] == "champions"
    assert body["total_members"] == 1

    filtered = api.get(
        "/v1/backoffice/segments?segment=loyal", headers=headers
    )
    assert filtered.status_code == 200
    assert filtered.json()["members"] == []

    invalid = api.get(
        "/v1/backoffice/segments?segment=unknown", headers=headers
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    run = api.post("/v1/backoffice/segments/run", headers=headers)
    assert run.status_code == 202
    assert run.json()["classified"] == 1
    assert run.json()["policy_version"] == "dec-011-v1"

    export = api.get("/v1/backoffice/segments/export", headers=headers)
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"rfm-all-" in export.headers["content-disposition"]
    assert "customer_id,email,display_name" in export.text
    assert "champions" in export.text


def test_segmentation_csv_neutralizes_spreadsheet_formulas() -> None:
    segmentation = FakeSegmentation()
    segmentation.display_name = "=SUM(1,2)"
    api = client(segmentation=segmentation)
    export = api.get(
        "/v1/backoffice/segments/export",
        headers={"authorization": "Bearer operator-token"},
    )
    assert export.status_code == 200
    assert "'=SUM(1,2)" in export.text


def test_risk_queue_and_model_routes_require_capability() -> None:
    api = client()
    assert api.get("/v1/backoffice/risk").status_code == 401
    denied = api.get(
        "/v1/backoffice/risk",
        headers={"authorization": "Bearer customer-token"},
    )
    assert denied.status_code == 403

    headers = {"authorization": "Bearer operator-token"}
    queue = api.get("/v1/backoffice/risk", headers=headers)
    assert queue.status_code == 200
    item = queue.json()[0]
    assert item["model_version"] == "logistic-regression-fraud-v1"
    assert item["reasons"] == ["model_score_at_or_above_threshold"]

    model = api.get("/v1/backoffice/risk/model", headers=headers)
    assert model.status_code == 200
    assert model.json()["version_label"] == "logistic-regression-fraud-v1"
    assert float(model.json()["threshold"]) <= 0.70
    assert model.json()["metrics"]["recall"] >= 0.80
    assert (
        api.get(
            "/v1/backoffice/risk/model",
            headers={"authorization": "Bearer customer-token"},
        ).status_code
        == 403
    )


def test_operator_order_routes_require_capability_and_return_customer_context() -> None:
    api = client()
    assert api.get("/v1/backoffice/orders").status_code == 401
    denied = api.get(
        "/v1/backoffice/orders",
        headers={"authorization": "Bearer customer-token"},
    )
    assert denied.status_code == 403

    headers = {"authorization": "Bearer operator-token"}
    listing = api.get("/v1/backoffice/orders", headers=headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["status"] is None
    row = body["items"][0]
    assert row["customer"]["email"] == "customer@example.invalid"
    assert row["status"] == "review"
    assert row["refund_total"] == "0"

    filtered = api.get("/v1/backoffice/orders?status=confirmed", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 0
    assert filtered.json()["status"] == "confirmed"

    invalid = api.get("/v1/backoffice/orders?status=unknown", headers=headers)
    assert invalid.status_code == 422

    detail = api.get(
        "/v1/backoffice/orders/70000000-0000-4000-8000-000000000001",
        headers=headers,
    )
    assert detail.status_code == 200
    order = detail.json()
    assert order["shipping"]["city"] == "Cairo"
    assert order["items"][0]["product_name"] == "X1 Phone"
    assert order["shipment"] is None
    assert (
        api.get(
            "/v1/backoffice/orders/70000000-0000-4000-8000-000000000001",
            headers={"authorization": "Bearer customer-token"},
        ).status_code
        == 403
    )


def test_operator_order_lifecycle_routes_require_write_capability() -> None:
    api = client()
    order_id = "70000000-0000-4000-8000-000000000001"
    operator = {"authorization": "Bearer operator-token"}
    customer = {"authorization": "Bearer customer-token"}

    assert api.post(f"/v1/backoffice/orders/{order_id}/shipment").status_code == 401
    assert (
        api.post(
            f"/v1/backoffice/orders/{order_id}/shipment",
            headers=customer,
            json={"status": "ready"},
        ).status_code
        == 403
    )

    transition = api.post(
        f"/v1/backoffice/orders/{order_id}/shipment",
        headers=operator,
        json={"status": "ready"},
    )
    assert transition.status_code == 200, transition.text
    assert transition.json()["status"] == "ready"
    assert transition.json()["events"][-1]["status"] == "ready"

    invalid_status = api.post(
        f"/v1/backoffice/orders/{order_id}/shipment",
        headers=operator,
        json={"status": "pending"},
    )
    assert invalid_status.status_code == 422

    cancellation = api.post(
        f"/v1/backoffice/orders/{order_id}/cancel",
        headers=operator,
        json={"reason": "Customer requested cancellation"},
    )
    assert cancellation.status_code == 200, cancellation.text
    body = cancellation.json()
    assert body["status"] == "cancelled"
    assert body["kind"] == "cancellation"
    assert body["amount"] == "0"
    assert body["refund_total"] == "0"

    short_reason = api.post(
        f"/v1/backoffice/orders/{order_id}/cancel",
        headers=operator,
        json={"reason": "x"},
    )
    assert short_reason.status_code == 422

    refund = api.post(
        f"/v1/backoffice/orders/{order_id}/refund",
        headers=operator,
        json={"amount": "2500", "reason": "Damaged item"},
    )
    assert refund.status_code == 200, refund.text
    assert refund.json()["status"] == "refunded"
    assert refund.json()["kind"] == "refund"
    assert refund.json()["amount"] == "2500"
    assert refund.json()["refund_total"] == "2500"

    negative_refund = api.post(
        f"/v1/backoffice/orders/{order_id}/refund",
        headers=operator,
        json={"amount": "-5", "reason": "Damaged item"},
    )
    assert negative_refund.status_code == 422

    adjustment = api.post(
        f"/v1/backoffice/inventory/{PRODUCT_ID}/adjustments",
        headers=operator,
        json={"quantity_delta": 5, "reason": "Stock count correction"},
    )
    assert adjustment.status_code == 200, adjustment.text
    assert adjustment.json()["on_hand"] == 15
    assert adjustment.json()["available"] == 13

    assert (
        api.post(
            f"/v1/backoffice/inventory/{PRODUCT_ID}/adjustments",
            headers=customer,
            json={"quantity_delta": 5, "reason": "Stock count correction"},
        ).status_code
        == 403
    )
    zero = api.post(
        f"/v1/backoffice/inventory/{PRODUCT_ID}/adjustments",
        headers=operator,
        json={"quantity_delta": 0, "reason": "Stock count correction"},
    )
    assert zero.status_code == 422

def test_analytics_route_requires_capability_and_validates_range() -> None:
    api = client()
    assert api.get("/v1/backoffice/analytics?from=2026-09-01&to=2026-09-28").status_code == 401
    denied = api.get(
        "/v1/backoffice/analytics?from=2026-09-01&to=2026-09-28",
        headers={"authorization": "Bearer customer-token"},
    )
    assert denied.status_code == 403

    headers = {"authorization": "Bearer operator-token"}
    report = api.get(
        "/v1/backoffice/analytics?from=2026-09-01&to=2026-09-28", headers=headers
    )
    assert report.status_code == 200
    body = report.json()
    assert body["behaviour"]["orders_per_session"] == "0.2"
    assert body["financial"]["net_sales"] == "55000"
    assert body["scope"]["date_from"] == "2026-09-01"
    assert body["reconciliation"][0]["matches"] is True
    assert any("Profit is not displayed" in item for item in body["definitions"])

    filtered = api.get(
        "/v1/backoffice/analytics?from=2026-09-01&to=2026-09-28&category=phones",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["scope"]["category"] == "phones"

    missing = api.get("/v1/backoffice/analytics?from=2026-09-01", headers=headers)
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "validation_error"


# --------------------------------------------------------------------- identity


def test_register_returns_a_customer_session_and_profile() -> None:
    identity = FakeIdentity()
    api = client(identity=identity)

    response = api.post(
        "/v1/auth/register",
        json={
            "email": "new@example.invalid",
            "display_name": "New Customer",
            "password": "demo-password-9",
            "preferred_locale": "en",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["surface"] == "customer"
    assert body["account"]["account_type"] == "customer"
    assert body["account"]["profile"]["email"] == "new@example.invalid"
    assert body["account"]["profile"]["preferred_locale"] == "en"
    assert identity.last_registration is not None


def test_login_rejects_unknown_credentials_and_rate_limits_failures() -> None:
    api = client(identity=FakeIdentity())

    for _ in range(10):
        response = api.post(
            "/v1/auth/login",
            json={
                "email": "customer@example.invalid",
                "password": "wrong-password",
                "surface": "customer",
            },
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    limited = api.post(
        "/v1/auth/login",
        json={
            "email": "customer@example.invalid",
            "password": "wrong-password",
            "surface": "customer",
        },
    )
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"


def test_customer_and_operator_surfaces_are_isolated() -> None:
    identity = FakeIdentity()
    api = client(identity=identity)

    customer = api.post(
        "/v1/auth/login",
        json={
            "email": "customer@example.invalid",
            "password": "demo-customer-1",
            "surface": "customer",
        },
    )
    operator = api.post(
        "/v1/auth/login",
        json={
            "email": "operator@example.invalid",
            "password": "demo-operator-1",
            "surface": "operator",
        },
    )
    assert customer.status_code == 200
    assert operator.status_code == 200

    customer_headers = {"authorization": f"Bearer {customer.json()['token']}"}
    operator_headers = {"authorization": f"Bearer {operator.json()['token']}"}

    me = api.get("/v1/auth/me", headers=customer_headers)
    assert me.status_code == 200
    assert me.json()["account_type"] == "customer"
    assert me.json()["profile"]["display_name"] == "Synthetic Customer"

    assert api.get("/v1/account", headers=customer_headers).status_code == 200
    assert api.get("/v1/orders", headers=customer_headers).status_code == 200
    assert api.get("/v1/account", headers=operator_headers).status_code == 403
    assert api.get("/v1/orders", headers=operator_headers).status_code == 403

    operator_me = api.get("/v1/auth/me", headers=operator_headers)
    assert operator_me.status_code == 200
    assert operator_me.json()["account_type"] == "backoffice"
    assert operator_me.json()["profile"] is None


def test_account_update_and_logout_revoke_the_session() -> None:
    identity = FakeIdentity()
    api = client(identity=identity)
    token = api.post(
        "/v1/auth/login",
        json={
            "email": "customer@example.invalid",
            "password": "demo-customer-1",
            "surface": "customer",
        },
    ).json()["token"]
    headers = {"authorization": f"Bearer {token}"}

    updated = api.patch(
        "/v1/account",
        headers=headers,
        json={"display_name": "Renamed Demo", "preferred_locale": "en"},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Renamed Demo"
    assert updated.json()["preferred_locale"] == "en"

    orders = api.get("/v1/orders?limit=5&offset=0", headers=headers)
    assert orders.status_code == 200
    assert orders.json()["total"] == 1
    assert orders.json()["items"][0]["item_count"] == 1

    assert api.post("/v1/auth/logout", headers=headers).status_code == 204
    assert api.get("/v1/auth/me", headers=headers).status_code == 401
    assert api.get("/v1/account", headers=headers).status_code == 401
