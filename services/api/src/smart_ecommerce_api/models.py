"""Public catalog response models."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Price(StrictModel):
    amount: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,13})(\.[0-9]{1,6})?$")]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    updated_at: datetime


class Availability(StrictModel):
    status: Literal["in_stock", "out_of_stock"]
    updated_at: datetime


class Image(StrictModel):
    uri: Annotated[str, Field(pattern=r"^https://[^\s]+$")]
    alt: Annotated[str, Field(max_length=500)]


class Product(StrictModel):
    product_id: UUID
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=10_000)]
    categories: list[str]
    attributes: dict[str, str]
    images: list[Image]
    price: Price
    availability: Availability


class ProductPage(StrictModel):
    items: Annotated[list[Product], Field(max_length=100)]
    total: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=100)]
    offset: Annotated[int, Field(ge=0)]


class FacetOption(StrictModel):
    value: str
    count: Annotated[int, Field(ge=1)]


class Facet(StrictModel):
    key: str
    options: list[FacetOption]


class CatalogFacets(StrictModel):
    total: Annotated[int, Field(ge=0)]
    facets: list[Facet]


class Health(StrictModel):
    status: str

