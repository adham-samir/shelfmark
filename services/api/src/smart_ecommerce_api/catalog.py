"""Cross-store catalog composition.

PostgreSQL owns product lifecycle, current price, and availability. MongoDB owns
descriptive product content. Missing active-product counterparts are reported as
an unavailable dependency; they are never converted to zero stock or empty copy.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from typing import Any, Literal, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient
from pydantic import ValidationError

from . import db
from .errors import DependencyUnavailable, ProductNotFound
from .models import (
    Availability,
    CatalogFacets,
    Facet,
    FacetOption,
    Image,
    Price,
    Product,
    ProductPage,
)


@dataclass(frozen=True, slots=True)
class OperationalProduct:
    product_id: UUID
    amount: Decimal
    currency: str
    price_updated_at: datetime
    available: int
    inventory_updated_at: datetime


class OperationalCatalog(Protocol):
    def list_active(self) -> list[OperationalProduct]: ...
    def get_active(self, product_id: UUID) -> OperationalProduct | None: ...
    def ping(self) -> None: ...


class DescriptiveCatalog(Protocol):
    def get_many(self, product_ids: list[UUID]) -> dict[str, dict[str, Any]]: ...
    def get_one(self, product_id: UUID) -> dict[str, Any] | None: ...
    def product_ids_for_category(self, category: str) -> list[str]: ...
    def ping(self) -> None: ...


class PostgresOperationalCatalog:
    _SELECT = """
        SELECT r.product_id, p.amount, p.currency,
               p.updated_at AS price_updated_at,
               i.available, i.updated_at AS inventory_updated_at
        FROM product_registry AS r
        LEFT JOIN product_prices AS p USING (product_id)
        LEFT JOIN inventory_balances AS i USING (product_id)
        WHERE r.lifecycle = 'active'
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @staticmethod
    def _record(row: dict[str, Any]) -> OperationalProduct:
        required = (
            "amount",
            "currency",
            "price_updated_at",
            "available",
            "inventory_updated_at",
        )
        if any(row.get(field) is None for field in required):
            raise DependencyUnavailable(
                "An active product is missing price or inventory data."
            )
        return OperationalProduct(**row)

    def list_active(self) -> list[OperationalProduct]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(self._SELECT + " ORDER BY r.product_id").fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable() from error
        return [self._record(row) for row in rows]

    def get_active(self, product_id: UUID) -> OperationalProduct | None:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    self._SELECT + " AND r.product_id = %s", (product_id,)
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable() from error
        return self._record(row) if row else None

    def ping(self) -> None:
        try:
            with db.connection(self._dsn) as connection:
                connection.execute("SELECT 1")
        except psycopg.Error as error:
            raise DependencyUnavailable() from error


class MongoDescriptiveCatalog:
    def __init__(self, uri: str, database: str) -> None:
        self._client: MongoClient[dict[str, Any]] = MongoClient(
            uri, serverSelectionTimeoutMS=2_000
        )
        self._database = self._client[database]

    def get_many(self, product_ids: list[UUID]) -> dict[str, dict[str, Any]]:
        if not product_ids:
            return {}
        identifiers = [str(product_id) for product_id in product_ids]
        try:
            records = self._database.products.find({"_id": {"$in": identifiers}})
            return {record["_id"]: record for record in records}
        except Exception as error:
            raise DependencyUnavailable() from error

    def get_one(self, product_id: UUID) -> dict[str, Any] | None:
        try:
            return self._database.products.find_one({"_id": str(product_id)})
        except Exception as error:
            raise DependencyUnavailable() from error

    def product_ids_for_category(self, category: str) -> list[str]:
        try:
            records = self._database.products.find(
                {"categories": {"$regex": f"^{re.escape(category)}$", "$options": "i"}},
                {"_id": 1},
            )
            return [record["_id"] for record in records]
        except Exception as error:
            raise DependencyUnavailable() from error

    def ping(self) -> None:
        try:
            self._client.admin.command("ping")
        except Exception as error:
            raise DependencyUnavailable() from error


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


CatalogSort = Literal["relevance", "price_asc", "price_desc", "name_asc"]


class CatalogService:
    def __init__(
        self, operational: OperationalCatalog, descriptive: DescriptiveCatalog
    ) -> None:
        self._operational = operational
        self._descriptive = descriptive

    def product_ids_for_category(self, category: str) -> list[UUID]:
        """Resolve a category to catalog product identifiers.

        Used by analytics to scope metrics without composing every product.
        A catalog outage fails closed instead of returning an empty scope.
        """

        try:
            return [
                UUID(value)
                for value in self._descriptive.product_ids_for_category(category)
            ]
        except ValueError as error:
            raise DependencyUnavailable(
                "The catalog returned an invalid product identifier."
            ) from error

    @staticmethod
    def _compose(
        operational: OperationalProduct, descriptive: dict[str, Any]
    ) -> Product:
        try:
            return Product(
                product_id=operational.product_id,
                name=descriptive["name"],
                description=descriptive.get("description", ""),
                categories=descriptive.get("categories", []),
                attributes=descriptive.get("attributes", {}),
                images=[Image(**image) for image in descriptive.get("images", [])],
                price=Price(
                    amount=_decimal_text(operational.amount),
                    currency=operational.currency,
                    updated_at=operational.price_updated_at,
                ),
                availability=Availability(
                    status="in_stock" if operational.available > 0 else "out_of_stock",
                    updated_at=operational.inventory_updated_at,
                ),
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise DependencyUnavailable(
                "An active product has invalid catalog content."
            ) from error

    def list_products(
        self,
        *,
        query: str | None,
        category: str | None,
        limit: int,
        offset: int,
        filters: dict[str, str] | None = None,
        sort: CatalogSort = "relevance",
        availability: Literal["in_stock", "out_of_stock"] | None = None,
        price_min: Decimal | None = None,
        price_max: Decimal | None = None,
    ) -> ProductPage:
        operational = self._operational.list_active()
        descriptions = self._descriptive.get_many(
            [record.product_id for record in operational]
        )
        missing = [
            str(record.product_id)
            for record in operational
            if str(record.product_id) not in descriptions
        ]
        if missing:
            raise DependencyUnavailable("An active product is missing catalog content.")

        products = [
            self._compose(record, descriptions[str(record.product_id)])
            for record in operational
        ]
        if query is not None:
            terms = self._search_terms(query)
            products = [
                product
                for product in products
                if all(term in self._search_text(product) for term in terms)
            ]
        if category is not None:
            products = [
                product
                for product in products
                if category.casefold() in {item.casefold() for item in product.categories}
            ]
        for key, value in (filters or {}).items():
            products = [
                product
                for product in products
                if product.attributes.get(key, "").casefold() == value.casefold()
            ]
        if availability is not None:
            products = [
                product
                for product in products
                if product.availability.status == availability
            ]
        if price_min is not None:
            products = [
                product for product in products if Decimal(product.price.amount) >= price_min
            ]
        if price_max is not None:
            products = [
                product for product in products if Decimal(product.price.amount) <= price_max
            ]
        if sort == "price_asc":
            products.sort(key=lambda product: Decimal(product.price.amount))
        elif sort == "price_desc":
            products.sort(key=lambda product: Decimal(product.price.amount), reverse=True)
        elif sort == "name_asc":
            products.sort(key=lambda product: product.name.casefold())
        total = len(products)
        return ProductPage(
            items=products[offset : offset + limit],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def _normalize_term(value: str) -> str:
        value = value.casefold()
        return value[:-1] if len(value) > 3 and value.endswith("s") else value

    @classmethod
    def _search_terms(cls, query: str) -> list[str]:
        stopwords = {
            "a",
            "an",
            "the",
            "find",
            "for",
            "me",
            "please",
            "show",
            "want",
            "اريد",
            "أريد",
            "من",
            "فضلك",
            "اعرض",
            "لي",
        }
        terms = [
            cls._normalize_term(term)
            for term in re.findall(r"[\w]+", query, flags=re.UNICODE)
            if term.casefold() not in stopwords
        ]
        return terms or [cls._normalize_term(query.strip())]

    @classmethod
    def _search_text(cls, product: Product) -> frozenset[str]:
        raw = " ".join(
            [
                product.name,
                product.description,
                *product.categories,
                *product.attributes.keys(),
                *product.attributes.values(),
            ]
        )
        return frozenset(
            cls._normalize_term(term)
            for term in re.findall(r"[\w]+", raw, flags=re.UNICODE)
        )

    def facets(
        self,
        *,
        query: str | None,
        category: str | None,
        filters: dict[str, str] | None,
        availability: Literal["in_stock", "out_of_stock"] | None = None,
        price_min: Decimal | None = None,
        price_max: Decimal | None = None,
    ) -> CatalogFacets:
        page = self.list_products(
            query=query,
            category=category,
            filters=filters,
            availability=availability,
            price_min=price_min,
            price_max=price_max,
            limit=100,
            offset=0,
        )
        counts: dict[str, dict[str, int]] = {}
        for product in page.items:
            for value in product.categories:
                category_counts = counts.setdefault("category", {})
                category_counts[value] = category_counts.get(value, 0) + 1
            for key, value in product.attributes.items():
                attribute_counts = counts.setdefault(key, {})
                attribute_counts[value] = attribute_counts.get(value, 0) + 1
        facets = [
            Facet(
                key=key,
                options=[
                    FacetOption(value=value, count=count)
                    for value, count in sorted(values.items())
                ],
            )
            for key, values in sorted(counts.items())
        ]
        return CatalogFacets(total=page.total, facets=facets)

    def get_product(self, product_id: UUID) -> Product:
        operational = self._operational.get_active(product_id)
        if operational is None:
            raise ProductNotFound()
        descriptive = self._descriptive.get_one(product_id)
        if descriptive is None:
            raise DependencyUnavailable("The active product is missing catalog content.")
        return self._compose(operational, descriptive)

    def check_dependencies(self) -> None:
        self._operational.ping()
        self._descriptive.ping()

