"""Public models for commerce and interaction endpoints."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from .models import StrictModel


MoneyText = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,13})(\.[0-9]{1,6})?$")]
OrderState = Literal[
    "pending_payment",
    "pending_risk",
    "review",
    "confirmed",
    "payment_failed",
    "cancelled",
    "shipped",
    "delivered",
    "refunded",
]


class CartItemInput(StrictModel):
    product_id: UUID
    quantity: Annotated[int, Field(ge=0, le=99)]


class CartItem(StrictModel):
    product_id: UUID
    quantity: Annotated[int, Field(gt=0, le=99)]
    unit_price: MoneyText
    available: Annotated[int, Field(ge=0)]


class Cart(StrictModel):
    cart_id: UUID
    items: list[CartItem]
    currency: Literal["EGP"] = "EGP"
    subtotal: MoneyText


class ShippingAddress(StrictModel):
    """Delivery contact captured with the order. Synthetic sandbox use only."""

    recipient_name: Annotated[str, Field(min_length=2, max_length=120)]
    phone: Annotated[str, Field(pattern=r"^\+?[0-9][0-9 -]{6,19}$")]
    city: Annotated[str, Field(min_length=2, max_length=80)]
    address_line: Annotated[str, Field(min_length=5, max_length=300)]


class CheckoutInput(StrictModel):
    payment_token: Annotated[str, Field(pattern=r"^tok_sandbox_[A-Za-z0-9_-]{4,100}$")]
    idempotency_key: Annotated[str, Field(min_length=16, max_length=128)]
    shipping: ShippingAddress


class OrderStatus(StrictModel):
    order_id: UUID
    status: OrderState


class OrderSummary(StrictModel):
    order_id: UUID
    status: OrderState
    currency: Literal["EGP"]
    subtotal: MoneyText
    item_count: int
    created_at: datetime


class OrderList(StrictModel):
    items: list[OrderSummary]
    total: int
    limit: int
    offset: int


class OrderItem(StrictModel):
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: MoneyText
    line_total: MoneyText


class Order(StrictModel):
    order_id: UUID
    status: OrderState
    currency: Literal["EGP"]
    subtotal: MoneyText
    created_at: datetime
    items: list[OrderItem]


class OperatorCustomer(StrictModel):
    """Minimum customer identity an operator needs to fulfil an order."""

    customer_id: UUID
    email: str
    display_name: str


class OperatorShipping(StrictModel):
    recipient_name: str | None = None
    phone: str | None = None
    city: str | None = None
    address_line: str | None = None


class OperatorOrderSummary(StrictModel):
    order_id: UUID
    status: OrderState
    currency: Literal["EGP"]
    subtotal: MoneyText
    refund_total: MoneyText
    item_count: int
    created_at: datetime
    customer: OperatorCustomer


class OperatorOrderList(StrictModel):
    items: list[OperatorOrderSummary]
    total: int
    limit: int
    offset: int
    status: OrderState | None = None


class OperatorOrder(StrictModel):
    order_id: UUID
    status: OrderState
    currency: Literal["EGP"]
    subtotal: MoneyText
    refund_total: MoneyText
    created_at: datetime
    completed_at: datetime | None = None
    customer: OperatorCustomer
    shipping: OperatorShipping | None = None
    items: list[OrderItem]


class ShipmentEvent(StrictModel):
    status: Literal["pending", "ready", "in_transit", "delivered", "exception"]
    description_ar: str
    description_en: str
    occurred_at: datetime


class Shipment(StrictModel):
    shipment_id: UUID
    status: Literal["pending", "ready", "in_transit", "delivered", "exception"]
    updated_at: datetime
    events: list[ShipmentEvent]


class ShipmentTransitionInput(StrictModel):
    status: Literal["ready", "in_transit", "delivered", "exception"]


class OrderCancelInput(StrictModel):
    reason: Annotated[str, Field(min_length=3, max_length=300)]


class OrderRefundInput(StrictModel):
    amount: MoneyText
    reason: Annotated[str, Field(min_length=3, max_length=300)]


class OrderAdjustmentResult(StrictModel):
    order_id: UUID
    status: OrderState
    refund_total: MoneyText
    adjustment_id: UUID
    kind: Literal["cancellation", "refund"]
    amount: MoneyText
    created_at: datetime


class OrderAdjustment(StrictModel):
    """One audited operator or customer action on an order."""

    adjustment_id: UUID
    kind: Literal["cancellation", "refund"]
    amount: MoneyText
    reason: str
    reason_code: str | None = None
    actor_kind: Literal["customer", "operator"]
    actor_name: str
    created_at: datetime


ReorderSkipReason = Literal[
    "product_inactive",
    "price_unavailable",
    "out_of_stock",
    "quantity_capped",
]


class ReorderItem(StrictModel):
    product_id: UUID
    product_name: str
    quantity: Annotated[int, Field(gt=0, le=99)]


class ReorderSkipped(ReorderItem):
    reason: ReorderSkipReason


class ReorderResult(StrictModel):
    """Outcome of copying a past order into the cart. Nothing is silently dropped."""

    order_id: UUID
    cart: Cart
    added: list[ReorderItem]
    skipped: list[ReorderSkipped]


CancellationReason = Literal[
    "changed_mind",
    "ordered_by_mistake",
    "wrong_item",
    "found_cheaper",
    "delivery_too_slow",
    "other",
]


class CustomerCancelInput(StrictModel):
    """A customer cancellation. The free-text reason is required only for `other`."""

    reason_code: CancellationReason
    reason: Annotated[str, Field(min_length=3, max_length=300)] | None = None

    @field_validator("reason")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class InventoryAdjustmentInput(StrictModel):
    quantity_delta: Annotated[int, Field(ge=-10_000, le=10_000)]
    reason: Annotated[str, Field(min_length=3, max_length=300)]

    @field_validator("quantity_delta")
    @classmethod
    def _non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta must not be zero")
        return value


class InventoryAdjustmentResult(StrictModel):
    product_id: UUID
    on_hand: int
    reserved: int
    available: int
    movement_id: UUID
    occurred_at: datetime



class OperatorOrderDetail(OperatorOrder):
    """Full operator view: additive `shipment` and `adjustments`."""

    shipment: Shipment | None = None
    adjustments: list["OrderAdjustment"] = Field(default_factory=list)


class BrowsingEventInput(StrictModel):
    event_id: UUID
    session_id: UUID
    product_id: UUID
    event_type: Literal["view", "search_click", "compare", "add_to_cart"]
    occurred_at: datetime
    context: dict[str, Any] = Field(default_factory=dict)


class ReviewDecisionInput(StrictModel):
    decision: Literal["allow", "decline"]


class ReviewQueueItem(StrictModel):
    assessment_id: UUID
    order_id: UUID
    customer_id: UUID
    score: str | None
    outcome: Literal["review", "assessment_failed"]
    subtotal: MoneyText
    assessed_at: datetime
    model_version: str | None = None
    reasons: list[str] = Field(default_factory=list)


class ReviewDecisionResult(StrictModel):
    assessment_id: UUID
    order_id: UUID
    status: OrderState
