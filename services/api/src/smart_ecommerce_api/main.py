"""FastAPI entry point for the Stage 3 application."""

import csv
import io
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

import anyio.to_thread
from fastapi import Depends, FastAPI, File, Query, Request, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .addresses import Address, AddressInput, AddressList, AddressStore
from .analytics import AnalyticsResponse, AnalyticsService, AnalyticsStore
from .assistant import (
    AssistantRequest,
    AssistantResponse,
    AssistantService,
    FaqKnowledge,
    OpenAITextGenerator,
)
from .auth import Authenticator, PostgresSandboxAuthenticator, Principal
from .catalog import CatalogService, MongoDescriptiveCatalog, PostgresOperationalCatalog
from .commerce import CommerceService, PostgresCommerceStore
from .commerce_models import (
    BrowsingEventInput,
    Cart,
    CartItemInput,
    CheckoutInput,
    CustomerCancelInput,
    InventoryAdjustmentInput,
    InventoryAdjustmentResult,
    OperatorOrderDetail,
    OperatorOrderList,
    Order,
    OrderAdjustmentResult,
    OrderCancelInput,
    OrderList,
    OrderRefundInput,
    OrderState,
    OrderStatus,
    ReorderResult,
    ReviewDecisionInput,
    ReviewDecisionResult,
    ReviewQueueItem,
    Shipment,
    ShipmentTransitionInput,
)
from .config import Settings
from .errors import (
    ApplicationError,
    DependencyUnavailable,
    Forbidden,
    InvalidInput,
    Unauthorized,
)
from .fraud import (
    FraudEvidenceStore,
    FraudModelSummary,
    HybridRiskAssessor,
    ModelRiskAssessor,
)
from .identity import (
    AccountProfile,
    AccountUpdate,
    AccountView,
    AuthSession,
    IdentityStore,
    LoginInput,
    LoginThrottle,
    PasswordChange,
    PasswordChangeResult,
    RegisterInput,
)
from .models import CatalogFacets, Health, Product, ProductPage
from .observability import (
    ACCESS_EVENT,
    ERROR_EVENT,
    access_logger,
    configure_logging,
    error_logger,
    request_id_var,
)
from .pricing import (
    PricingObservationInput,
    PricingObservationResult,
    PricingOverviewResponse,
    PricingRunInput,
    PricingRunResult,
    PricingService,
    PricingStore,
    SeasonCalendar,
)
from .forecasting import (
    InventoryPlanningResponse,
    InventoryService,
    InventoryStore,
    ReorderRunResult,
    SandboxSupplierSimulator,
)
from .recommendation import RecommendationResult, RecommendationService, RecommendationStore
from .segmentation import (
    SegmentationResponse,
    SegmentationRunResult,
    SegmentationService,
    SegmentationStore,
    SegmentName,
)
from .search import (
    ImageSearchResponse,
    OpenAITranscriber,
    PyTorchImageRetriever,
    SearchEvidenceStore,
    SearchService,
    VoiceSearchResponse,
)


def _request_id(request: Request) -> str:
    return request.state.request_id


def _error_response(
    request: Request, *, status_code: int, code: str, message: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
            }
        },
    )


def _validated_request_id(value: str | None) -> str:
    if value is not None:
        try:
            return str(UUID(value))
        except ValueError:
            pass
    return str(uuid4())


def _parse_filters(values: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values or []:
        if ":" not in value:
            raise InvalidInput("Each filter must use the key:value format.")
        key, option = (part.strip() for part in value.split(":", 1))
        if not key or not option or key in parsed:
            raise InvalidInput("Filters require unique, non-empty keys and values.")
        parsed[key] = option
    return parsed


def _csv_cell(value: object) -> str:
    text = str(value)
    return f"'{text}" if text[:1] in {"=", "+", "-", "@"} else text


def create_app(
    catalog_service: CatalogService | None = None,
    commerce_service: CommerceService | None = None,
    authenticator: Authenticator | None = None,
    recommendation_service: RecommendationService | None = None,
    assistant_service: AssistantService | None = None,
    search_service: SearchService | None = None,
    inventory_service: InventoryService | None = None,
    pricing_service: PricingService | None = None,
    segmentation_service: SegmentationService | None = None,
    analytics_service: AnalyticsService | None = None,
    risk_model: ModelRiskAssessor | None = None,
    identity_store: IdentityStore | None = None,
    address_store: AddressStore | None = None,
    login_throttle: LoginThrottle | None = None,
    settings_factory: Callable[[], Settings] = Settings.from_environment,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Sync endpoints run on AnyIO worker threads. The 40-thread default queues
        # a 100-session burst in waves; size it to the DEC-014 concurrency baseline.
        anyio.to_thread.current_default_thread_limiter().total_tokens = (
            application.state.worker_threads
        )
        # Configured here rather than at import so a bare TestClient, which does
        # not run lifespan, keeps the stdlib logging defaults.
        configure_logging()
        yield

    app = FastAPI(
        title="Smart-eCommerce API",
        version="0.1.0",
        description="Stage 3 commerce and smart-eCommerce API.",
        lifespan=lifespan,
    )

    worker_threads = 100
    if (
        catalog_service is None
        or commerce_service is None
        or authenticator is None
        or recommendation_service is None
        or assistant_service is None
        or search_service is None
        or inventory_service is None
        or pricing_service is None
        or segmentation_service is None
        or analytics_service is None
        or risk_model is None
        or identity_store is None
        or address_store is None
    ):
        settings = settings_factory()
        worker_threads = settings.worker_threads

    app.state.worker_threads = worker_threads
    if risk_model is None:
        risk_model = ModelRiskAssessor(
            settings.fraud_artifact,
            FraudEvidenceStore(settings.postgres_dsn),
        )
    if catalog_service is None or commerce_service is None:
        descriptive = MongoDescriptiveCatalog(
            settings.mongo_uri, settings.mongo_database
        )
    if catalog_service is None:
        catalog_service = CatalogService(
            PostgresOperationalCatalog(settings.postgres_dsn),
            descriptive,
        )
    if commerce_service is None:
        commerce_service = CommerceService(
            PostgresCommerceStore(
                settings.postgres_dsn, HybridRiskAssessor(risk_model)
            ),
            descriptive,
        )
    if identity_store is None:
        identity_store = IdentityStore(settings.postgres_dsn)
    if address_store is None:
        address_store = AddressStore(settings.postgres_dsn)
    if authenticator is None:
        authenticator = identity_store
    if login_throttle is None:
        login_throttle = LoginThrottle()
    if recommendation_service is None:
        recommendation_service = RecommendationService(
            RecommendationStore(settings.postgres_dsn),
            settings.recommendation_artifact,
        )
    if assistant_service is None:
        assistant_service = AssistantService(
            catalog_service,
            commerce_service,
            FaqKnowledge(settings.assistant_knowledge),
            OpenAITextGenerator(settings.openai_api_key, settings.assistant_model),
        )
    if search_service is None:
        search_service = SearchService(
            catalog_service,
            PyTorchImageRetriever(settings.image_search_artifact),
            OpenAITranscriber(settings.openai_api_key, settings.transcription_model),
            settings.maximum_upload_bytes,
            SearchEvidenceStore(
                settings.postgres_dsn,
                settings.image_search_artifact,
            ),
        )
    if inventory_service is None:
        inventory_service = InventoryService(
            InventoryStore(settings.postgres_dsn),
            settings.forecast_artifact,
            SandboxSupplierSimulator(),
        )
    if pricing_service is None:
        pricing_service = PricingService(
            PricingStore(settings.postgres_dsn),
            SeasonCalendar(settings.pricing_seasons),
        )
    if segmentation_service is None:
        segmentation_service = SegmentationService(
            SegmentationStore(settings.postgres_dsn)
        )
    if analytics_service is None:
        analytics_service = AnalyticsService(
            AnalyticsStore(settings.postgres_dsn), catalog_service
        )
    app.state.catalog_service = catalog_service
    app.state.commerce_service = commerce_service
    app.state.authenticator = authenticator
    app.state.recommendation_service = recommendation_service
    app.state.assistant_service = assistant_service
    app.state.search_service = search_service
    app.state.inventory_service = inventory_service
    app.state.pricing_service = pricing_service
    app.state.segmentation_service = segmentation_service
    app.state.analytics_service = analytics_service
    app.state.risk_model = risk_model
    app.state.identity_store = identity_store
    app.state.address_store = address_store
    app.state.login_throttle = login_throttle

    bearer = HTTPBearer(auto_error=False)

    def current_principal(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> Principal:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise Unauthorized()
        return app.state.authenticator.authenticate(credentials.credentials)

    def presented_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> str:
        """The raw bearer value, needed only where a route must spare its own session."""
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise Unauthorized()
        return credentials.credentials

    def current_customer(
        principal: Principal = Depends(current_principal),
    ) -> Principal:
        if principal.account_type != "customer" or principal.customer_id is None:
            raise Forbidden()
        return principal

    def require_scope(scope: str):
        def dependency(
            principal: Principal = Depends(current_principal),
        ) -> Principal:
            if principal.account_type != "backoffice" or scope not in principal.scopes:
                raise Forbidden()
            return principal

        return dependency

    @app.middleware("http")
    async def request_identifier(request: Request, call_next):
        request.state.request_id = _validated_request_id(
            request.headers.get("x-request-id")
        )
        token = request_id_var.set(request.state.request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # The exception handlers turn this into a 500, but the access line
            # must still be written, and the traceback must reach the log.
            access_logger().exception(
                ACCESS_EVENT,
                extra={
                    "event": ACCESS_EVENT,
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "request_id": request.state.request_id,
                },
            )
            raise
        finally:
            request_id_var.reset(token)
        duration_ms = int((time.perf_counter() - started) * 1000)
        access_logger().info(
            ACCESS_EVENT,
            extra={
                "event": ACCESS_EVENT,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request.state.request_id,
            },
        )
        response.headers["x-request-id"] = request.state.request_id
        # The API serves JSON only, so it can afford a policy stricter than the
        # storefront's. Nothing here is meant to be framed or sniffed.
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("referrer-policy", "no-referrer")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault(
            "permissions-policy", "geolocation=(), microphone=(), camera=()"
        )
        # The interactive docs page loads its assets from a CDN, so the strict
        # JSON-only policy is applied everywhere except the docs surface.
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers.setdefault(
                "content-security-policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        return response

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, error: ApplicationError):
        # 4xx is the caller's mistake and needs no traceback; 5xx is ours.
        log = error_logger()
        level = logging.ERROR if error.status_code >= 500 else logging.WARNING
        log.log(
            level,
            ERROR_EVENT,
            extra={
                "event": ERROR_EVENT,
                "code": error.code,
                "status": error.status_code,
                "method": request.method,
                "path": request.url.path,
                "request_id": _request_id(request),
            },
        )
        return _error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _error: RequestValidationError):
        error_logger().warning(
            ERROR_EVENT,
            extra={
                "event": ERROR_EVENT,
                "code": "validation_error",
                "status": 422,
                "method": request.method,
                "path": request.url.path,
                "request_id": _request_id(request),
            },
        )
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="The request is invalid.",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        # Log the traceback here: the client receives only a generic message.
        error_logger().error(
            ERROR_EVENT,
            extra={
                "event": ERROR_EVENT,
                "code": "internal_error",
                "status": 500,
                "method": request.method,
                "path": request.url.path,
                "request_id": _request_id(request),
            },
            exc_info=error,
        )
        return _error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )

    @app.get("/health/live", response_model=Health, tags=["health"])
    def live() -> Health:
        return Health(status="live")

    @app.get(
        "/health/ready",
        response_model=Health,
        responses={503: {"description": "A required database is unavailable."}},
        tags=["health"],
    )
    def ready() -> Health:
        try:
            app.state.catalog_service.check_dependencies()
        except DependencyUnavailable:
            raise
        return Health(status="ready")

    def throttle_key(request: Request, identifier: str) -> str:
        host = request.client.host if request.client is not None else "unknown"
        return f"{identifier.strip().lower()}:{host}"

    @app.post(
        "/v1/auth/register",
        response_model=AuthSession,
        status_code=status.HTTP_201_CREATED,
        responses={
            409: {"description": "The email already has an account."},
            422: {"description": "The registration is invalid."},
            503: {"description": "The identity store is unavailable."},
        },
        tags=["identity"],
    )
    def register_account(registration: RegisterInput) -> AuthSession:
        return app.state.identity_store.register(registration)

    @app.post(
        "/v1/auth/login",
        response_model=AuthSession,
        responses={
            401: {"description": "Unknown account or wrong password."},
            429: {"description": "Too many failed attempts."},
            503: {"description": "The identity store is unavailable."},
        },
        tags=["identity"],
    )
    def login(request: Request, credentials: LoginInput) -> AuthSession:
        key = throttle_key(request, credentials.email)
        app.state.login_throttle.check(key)
        try:
            session = app.state.identity_store.login(credentials)
        except Unauthorized:
            app.state.login_throttle.failure(key)
            raise
        app.state.login_throttle.success(key)
        return session

    @app.post(
        "/v1/auth/logout",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["identity"],
    )
    def logout(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> Response:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise Unauthorized()
        app.state.identity_store.revoke(credentials.credentials)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/v1/auth/me",
        response_model=AccountView,
        tags=["identity"],
    )
    def whoami(principal: Principal = Depends(current_principal)) -> AccountView:
        return app.state.identity_store.view(principal)

    @app.get(
        "/v1/account",
        response_model=AccountProfile,
        tags=["identity", "commerce"],
    )
    def get_account(principal: Principal = Depends(current_customer)) -> AccountProfile:
        return app.state.identity_store.profile(principal.customer_id)

    @app.patch(
        "/v1/account",
        response_model=AccountProfile,
        tags=["identity", "commerce"],
    )
    def update_account(
        update: AccountUpdate,
        principal: Principal = Depends(current_customer),
    ) -> AccountProfile:
        return app.state.identity_store.update_profile(principal.customer_id, update)

    @app.post(
        "/v1/account/password",
        response_model=PasswordChangeResult,
        responses={401: {"description": "The current password is incorrect."}},
        tags=["identity"],
    )
    def change_account_password(
        change: PasswordChange,
        principal: Principal = Depends(current_customer),
        token: str = Depends(presented_token),
    ) -> PasswordChangeResult:
        return app.state.identity_store.change_password(principal, token, change)

    @app.get(
        "/v1/addresses",
        response_model=AddressList,
        tags=["identity", "commerce"],
    )
    def list_addresses(
        principal: Principal = Depends(current_customer),
    ) -> AddressList:
        return app.state.address_store.list(principal.customer_id)

    @app.post(
        "/v1/addresses",
        response_model=Address,
        status_code=status.HTTP_201_CREATED,
        responses={409: {"description": "Address book is full."}},
        tags=["identity", "commerce"],
    )
    def create_address(
        address: AddressInput,
        principal: Principal = Depends(current_customer),
    ) -> Address:
        return app.state.address_store.create(principal.customer_id, address)

    @app.put(
        "/v1/addresses/{address_id}",
        response_model=Address,
        responses={
            404: {"description": "Address not found for this customer."},
            409: {"description": "The default address cannot be cleared."},
        },
        tags=["identity", "commerce"],
    )
    def update_address(
        address_id: UUID,
        address: AddressInput,
        principal: Principal = Depends(current_customer),
    ) -> Address:
        return app.state.address_store.update(
            principal.customer_id, address_id, address
        )

    @app.delete(
        "/v1/addresses/{address_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={404: {"description": "Address not found for this customer."}},
        tags=["identity", "commerce"],
    )
    def delete_address(
        address_id: UUID,
        principal: Principal = Depends(current_customer),
    ) -> Response:
        app.state.address_store.delete(principal.customer_id, address_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/v1/orders",
        response_model=OrderList,
        tags=["commerce"],
    )
    def list_orders(
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        principal: Principal = Depends(current_customer),
    ) -> OrderList:
        return app.state.commerce_service.list_orders(
            principal.customer_id, limit=limit, offset=offset
        )

    @app.get(
        "/v1/products",
        response_model=ProductPage,        responses={503: {"description": "Catalog dependency unavailable."}},
        tags=["catalog"],
    )
    def list_products(
        q: Annotated[
            str | None,
            Query(min_length=1, max_length=200, pattern=r"\S"),
        ] = None,
        category: Annotated[
            str | None,
            Query(min_length=1, max_length=100, pattern=r"\S"),
        ] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        filter_values: Annotated[list[str] | None, Query(alias="filter")] = None,
        sort: Annotated[
            Literal["relevance", "price_asc", "price_desc", "name_asc"],
            Query(description="Result ordering applied before pagination."),
        ] = "relevance",
        availability: Annotated[
            Literal["in_stock", "out_of_stock"] | None,
            Query(description="Operational availability filter."),
        ] = None,
        price_min: Annotated[Decimal | None, Query(ge=0)] = None,
        price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    ) -> ProductPage:
        return app.state.catalog_service.list_products(
            query=q,
            category=category,
            filters=_parse_filters(filter_values),
            limit=limit,
            offset=offset,
            sort=sort,
            availability=availability,
            price_min=price_min,
            price_max=price_max,
        )

    @app.get(
        "/v1/products/facets",
        response_model=CatalogFacets,
        tags=["catalog", "smart-storefront"],
    )
    def product_facets(
        q: Annotated[
            str | None,
            Query(min_length=1, max_length=200, pattern=r"\S"),
        ] = None,
        category: Annotated[
            str | None,
            Query(min_length=1, max_length=100, pattern=r"\S"),
        ] = None,
        filter_values: Annotated[list[str] | None, Query(alias="filter")] = None,
        availability: Annotated[
            Literal["in_stock", "out_of_stock"] | None, Query()
        ] = None,
        price_min: Annotated[Decimal | None, Query(ge=0)] = None,
        price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    ) -> CatalogFacets:
        return app.state.catalog_service.facets(
            query=q,
            category=category,
            filters=_parse_filters(filter_values),
            availability=availability,
            price_min=price_min,
            price_max=price_max,
        )

    @app.get(
        "/v1/products/{product_id}",
        response_model=Product,
        responses={
            404: {"description": "Unknown or inactive product."},
            503: {"description": "Catalog dependency unavailable."},
        },
        tags=["catalog"],
    )
    def get_product(product_id: UUID) -> Product:
        return app.state.catalog_service.get_product(product_id)

    @app.post(
        "/v1/events/browsing",
        status_code=status.HTTP_202_ACCEPTED,
        tags=["interactions"],
    )
    def record_browsing_event(
        event: BrowsingEventInput,
        principal: Principal = Depends(current_customer),
    ) -> Response:
        app.state.commerce_service.record_event(
            principal.customer_id,
            event_id=event.event_id,
            session_id=event.session_id,
            product_id=event.product_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            context=event.context,
        )
        return Response(status_code=status.HTTP_202_ACCEPTED)

    @app.get("/v1/cart", response_model=Cart, tags=["commerce"])
    def get_cart(principal: Principal = Depends(current_customer)) -> Cart:
        return app.state.commerce_service.get_cart(principal.customer_id)

    @app.put("/v1/cart/items", response_model=Cart, tags=["commerce"])
    def set_cart_item(
        item: CartItemInput,
        principal: Principal = Depends(current_customer),
    ) -> Cart:
        return app.state.commerce_service.set_cart_item(
            principal.customer_id, item.product_id, item.quantity
        )

    @app.post(
        "/v1/checkout",
        response_model=OrderStatus,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["commerce", "risk"],
    )
    def checkout(
        checkout_input: CheckoutInput,
        principal: Principal = Depends(current_customer),
    ) -> OrderStatus:
        return app.state.commerce_service.checkout(
            principal.customer_id,
            checkout_input.payment_token,
            checkout_input.idempotency_key,
            checkout_input.shipping,
        )

    @app.get("/v1/orders/{order_id}", response_model=Order, tags=["commerce"])
    def get_order(
        order_id: UUID,
        principal: Principal = Depends(current_customer),
    ) -> Order:
        return app.state.commerce_service.get_order(principal.customer_id, order_id)

    @app.post(
        "/v1/orders/{order_id}/reorder",
        response_model=ReorderResult,
        responses={404: {"description": "Order not found for this customer."}},
        tags=["commerce"],
    )
    def reorder_own_order(
        order_id: UUID,
        principal: Principal = Depends(current_customer),
    ) -> ReorderResult:
        return app.state.commerce_service.reorder(principal.customer_id, order_id)

    @app.post(
        "/v1/orders/{order_id}/cancel",
        response_model=OrderAdjustmentResult,
        responses={
            404: {"description": "Order not found for this customer."},
            409: {"description": "The order can no longer be cancelled."},
        },
        tags=["commerce"],
    )
    def cancel_own_order(
        order_id: UUID,
        cancellation: CustomerCancelInput,
        principal: Principal = Depends(current_customer),
    ) -> OrderAdjustmentResult:
        return app.state.commerce_service.customer_cancel_order(
            principal.customer_id,
            order_id,
            cancellation.reason_code,
            cancellation.reason,
            principal.principal_id,
        )

    @app.get(
        "/v1/orders/{order_id}/shipment",
        response_model=Shipment,
        tags=["commerce", "assistant"],
    )
    def get_shipment(
        order_id: UUID,
        principal: Principal = Depends(current_customer),
    ) -> Shipment:
        return app.state.commerce_service.get_shipment(
            principal.customer_id, order_id
        )

    @app.get(
        "/v1/backoffice/orders",
        response_model=OperatorOrderList,
        tags=["backoffice", "orders"],
    )
    def list_operator_orders(
        status_filter: Annotated[OrderState | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        _principal: Principal = Depends(require_scope("orders:read")),
    ) -> OperatorOrderList:
        return app.state.commerce_service.operator_list_orders(
            status=status_filter, limit=limit, offset=offset
        )

    @app.get(
        "/v1/backoffice/orders/{order_id}",
        response_model=OperatorOrderDetail,
        responses={404: {"description": "Order not found."}},
        tags=["backoffice", "orders"],
    )
    def get_operator_order(
        order_id: UUID,
        _principal: Principal = Depends(require_scope("orders:read")),
    ) -> OperatorOrderDetail:
        return app.state.commerce_service.operator_get_order(order_id)

    @app.post(
        "/v1/backoffice/orders/{order_id}/shipment",
        response_model=Shipment,
        responses={
            404: {"description": "Shipment not found."},
            409: {"description": "Illegal transition or closed order."},
        },
        tags=["backoffice", "orders"],
    )
    def transition_operator_shipment(
        order_id: UUID,
        transition: ShipmentTransitionInput,
        principal: Principal = Depends(require_scope("orders:write")),
    ) -> Shipment:
        return app.state.commerce_service.operator_transition_shipment(
            order_id, transition.status, principal.principal_id
        )

    @app.post(
        "/v1/backoffice/orders/{order_id}/cancel",
        response_model=OrderAdjustmentResult,
        responses={
            404: {"description": "Order not found."},
            409: {"description": "Order can no longer be cancelled."},
        },
        tags=["backoffice", "orders"],
    )
    def cancel_operator_order(
        order_id: UUID,
        cancellation: OrderCancelInput,
        principal: Principal = Depends(require_scope("orders:write")),
    ) -> OrderAdjustmentResult:
        return app.state.commerce_service.operator_cancel_order(
            order_id, cancellation.reason, principal.principal_id
        )

    @app.post(
        "/v1/backoffice/orders/{order_id}/refund",
        response_model=OrderAdjustmentResult,
        responses={
            404: {"description": "Order not found."},
            409: {"description": "Refund exceeds the remaining total."},
        },
        tags=["backoffice", "orders"],
    )
    def refund_operator_order(
        order_id: UUID,
        refund: OrderRefundInput,
        principal: Principal = Depends(require_scope("orders:write")),
    ) -> OrderAdjustmentResult:
        return app.state.commerce_service.operator_refund_order(
            order_id, refund.amount, refund.reason, principal.principal_id
        )

    @app.post(
        "/v1/backoffice/risk/{assessment_id}/decision",
        response_model=ReviewDecisionResult,
        tags=["backoffice", "risk"],
    )
    def decide_risk_review(
        assessment_id: UUID,
        review: ReviewDecisionInput,
        principal: Principal = Depends(require_scope("risk:review")),
    ) -> ReviewDecisionResult:
        return app.state.commerce_service.decide_review(
            principal.principal_id, assessment_id, review.decision
        )

    @app.get(
        "/v1/backoffice/risk",
        response_model=list[ReviewQueueItem],
        tags=["backoffice", "risk"],
    )
    def list_risk_reviews(
        _principal: Principal = Depends(require_scope("risk:review")),
    ) -> list[ReviewQueueItem]:
        return app.state.commerce_service.list_risk_reviews()

    @app.get(
        "/v1/backoffice/risk/model",
        response_model=FraudModelSummary,
        responses={503: {"description": "Fraud model artifact unavailable."}},
        tags=["backoffice", "risk"],
    )
    def get_fraud_model(
        _principal: Principal = Depends(require_scope("risk:review")),
    ) -> FraudModelSummary:
        return app.state.risk_model.summary()

    @app.get(
        "/v1/backoffice/inventory",
        response_model=InventoryPlanningResponse,
        tags=["backoffice", "inventory"],
    )
    def get_inventory_planning(
        _principal: Principal = Depends(require_scope("inventory:write")),
    ) -> InventoryPlanningResponse:
        return app.state.inventory_service.planning()

    @app.post(
        "/v1/backoffice/inventory/{product_id}/adjustments",
        response_model=InventoryAdjustmentResult,
        responses={
            404: {"description": "Inventory balance not found."},
            409: {"description": "Adjustment would undercut reserved stock."},
        },
        tags=["backoffice", "inventory"],
    )
    def adjust_inventory(
        product_id: UUID,
        adjustment: InventoryAdjustmentInput,
        principal: Principal = Depends(require_scope("inventory:write")),
    ) -> InventoryAdjustmentResult:
        return app.state.commerce_service.operator_adjust_inventory(
            product_id,
            adjustment.quantity_delta,
            adjustment.reason,
            principal.principal_id,
        )

    @app.post(
        "/v1/backoffice/reorders/run",
        response_model=ReorderRunResult,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["backoffice", "inventory"],
    )
    def run_reorder_evaluation(
        _principal: Principal = Depends(require_scope("inventory:write")),
    ) -> ReorderRunResult:
        return app.state.inventory_service.run()

    @app.get(
        "/v1/backoffice/pricing",
        response_model=PricingOverviewResponse,
        responses={503: {"description": "Pricing inputs or season calendar unavailable."}},
        tags=["backoffice", "pricing"],
    )
    def get_pricing_overview(
        _principal: Principal = Depends(require_scope("pricing:write")),
    ) -> PricingOverviewResponse:
        return app.state.pricing_service.overview()

    @app.post(
        "/v1/backoffice/pricing/run",
        response_model=PricingRunResult,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["backoffice", "pricing"],
    )
    def run_pricing_evaluation(
        run_input: PricingRunInput | None = None,
        _principal: Principal = Depends(require_scope("pricing:write")),
    ) -> PricingRunResult:
        return app.state.pricing_service.run(
            product_ids=run_input.product_ids if run_input else None
        )

    @app.post(
        "/v1/backoffice/pricing/observations",
        response_model=PricingObservationResult,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["backoffice", "pricing"],
    )
    def record_pricing_observation(
        observation: PricingObservationInput,
        _principal: Principal = Depends(require_scope("pricing:write")),
    ) -> PricingObservationResult:
        return app.state.pricing_service.record_observation(observation)

    @app.get(
        "/v1/backoffice/segments",
        response_model=SegmentationResponse,
        responses={503: {"description": "Order history or snapshots unavailable."}},
        tags=["backoffice", "segments"],
    )
    def get_customer_segments(
        reference_date: date | None = None,
        segment: SegmentName | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        _principal: Principal = Depends(require_scope("segments:read")),
    ) -> SegmentationResponse:
        return app.state.segmentation_service.overview(
            reference_date=reference_date,
            segment=segment,
            limit=limit,
            offset=offset,
        )

    @app.post(
        "/v1/backoffice/segments/run",
        response_model=SegmentationRunResult,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["backoffice", "segments"],
    )
    def run_customer_segmentation(
        _principal: Principal = Depends(require_scope("segments:read")),
    ) -> SegmentationRunResult:
        return app.state.segmentation_service.run()

    @app.get(
        "/v1/backoffice/segments/export",
        response_class=Response,
        responses={
            200: {
                "description": "Selected customer group as CSV.",
                "content": {"text/csv": {"schema": {"type": "string"}}},
            }
        },
        tags=["backoffice", "segments"],
    )
    def export_customer_segments(
        reference_date: date | None = None,
        segment: SegmentName | None = None,
        _principal: Principal = Depends(require_scope("segments:read")),
    ) -> Response:
        rows = app.state.segmentation_service.export_rows(
            reference_date=reference_date, segment=segment
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "customer_id",
                "email",
                "display_name",
                "reference_date",
                "recency_days",
                "frequency",
                "monetary",
                "recency_score",
                "frequency_score",
                "monetary_score",
                "segment",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    str(row.customer_id),
                    _csv_cell(row.email),
                    _csv_cell(row.display_name),
                    row.reference_date.isoformat(),
                    row.recency_days,
                    row.frequency,
                    str(row.monetary),
                    row.recency_score,
                    row.frequency_score,
                    row.monetary_score,
                    row.segment,
                ]
            )
        stamp = (reference_date or datetime.now(UTC).date()).isoformat()
        filename = f"rfm-{segment or 'all'}-{stamp}.csv"
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get(
        "/v1/backoffice/analytics",
        response_model=AnalyticsResponse,
        responses={
            422: {"description": "Invalid date range."},
            503: {"description": "Analytics source unavailable."},
        },
        tags=["backoffice", "analytics"],
    )
    def get_analytics(
        date_from: Annotated[date, Query(alias="from")],
        date_to: Annotated[date, Query(alias="to")],
        category: Annotated[
            str | None, Query(min_length=1, max_length=100, pattern=r"\S")
        ] = None,
        _principal: Principal = Depends(require_scope("analytics:read")),
    ) -> AnalyticsResponse:
        return app.state.analytics_service.report(
            date_from=date_from, date_to=date_to, category=category
        )

    @app.get(
        "/v1/recommendations",
        response_model=RecommendationResult,
        tags=["smart-storefront"],
    )
    def get_recommendations(
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
        principal: Principal = Depends(current_customer),
    ) -> RecommendationResult:
        return app.state.recommendation_service.recommend(
            principal.customer_id, limit
        )

    @app.post(
        "/v1/assistant/messages",
        response_model=AssistantResponse,
        tags=["assistant", "smart-storefront"],
    )
    def assistant_message(
        message: AssistantRequest,
        principal: Principal = Depends(current_customer),
    ) -> AssistantResponse:
        return app.state.assistant_service.answer(principal.customer_id, message)

    @app.post(
        "/v1/search/image",
        response_model=ImageSearchResponse,
        tags=["search", "smart-storefront"],
    )
    async def image_search(
        image: Annotated[UploadFile, File()],
        category: Annotated[
            str | None,
            Query(min_length=1, max_length=100, pattern=r"\S"),
        ] = None,
        filter_values: Annotated[list[str] | None, Query(alias="filter")] = None,
        limit: Annotated[int, Query(ge=1, le=20)] = 10,
    ) -> ImageSearchResponse:
        content = await image.read(app.state.search_service.maximum_upload_bytes + 1)
        return app.state.search_service.image_search(
            content=content,
            content_type=image.content_type or "application/octet-stream",
            category=category,
            filters=_parse_filters(filter_values),
            limit=limit,
        )

    @app.post(
        "/v1/search/voice",
        response_model=VoiceSearchResponse,
        tags=["search", "smart-storefront"],
    )
    async def voice_search(
        audio: Annotated[UploadFile, File()],
        locale: Annotated[Literal["ar", "en"], Query()] = "en",
        category: Annotated[
            str | None,
            Query(min_length=1, max_length=100, pattern=r"\S"),
        ] = None,
        filter_values: Annotated[list[str] | None, Query(alias="filter")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> VoiceSearchResponse:
        content = await audio.read(app.state.search_service.maximum_upload_bytes + 1)
        return app.state.search_service.voice_search(
            filename=audio.filename or "recording",
            content_type=audio.content_type or "application/octet-stream",
            content=content,
            language=locale,
            category=category,
            filters=_parse_filters(filter_values),
            limit=limit,
        )

    return app


app = create_app()

