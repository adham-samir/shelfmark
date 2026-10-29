"""Customer address book.

Orders keep their own frozen shipping snapshot; this module never touches order
history. At most one address per customer is the default.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import Field, field_validator

from . import db
from .errors import Conflict, DependencyUnavailable, InvalidInput, ResourceNotFound
from .models import StrictModel

MAX_ADDRESSES = 10

PHONE_PATTERN = r"^\+?[0-9][0-9 -]{6,19}$"


class AddressInput(StrictModel):
    label: Annotated[str, Field(min_length=1, max_length=60)]
    recipient_name: Annotated[str, Field(min_length=2, max_length=120)]
    phone: Annotated[str, Field(pattern=PHONE_PATTERN)]
    city: Annotated[str, Field(min_length=2, max_length=80)]
    address_line: Annotated[str, Field(min_length=5, max_length=300)]
    is_default: bool = False

    @field_validator("label", "recipient_name", "city", "address_line")
    @classmethod
    def _strip(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be blank")
        return text


class Address(AddressInput):
    address_id: UUID
    created_at: datetime
    updated_at: datetime


class AddressList(StrictModel):
    items: list[Address]
    limit: int


def _row(row: dict) -> Address:
    return Address(
        address_id=row["address_id"],
        label=row["label"],
        recipient_name=row["recipient_name"],
        phone=row["phone"],
        city=row["city"],
        address_line=row["address_line"],
        is_default=row["is_default"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class AddressStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def list(self, customer_id: UUID) -> AddressList:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT address_id, label, recipient_name, phone, city,
                           address_line, is_default, created_at, updated_at
                    FROM customer_addresses
                    WHERE customer_id = %s
                    ORDER BY is_default DESC, created_at, address_id
                    """,
                    (customer_id,),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("The address store is unavailable.") from error
        return AddressList(items=[_row(row) for row in rows], limit=MAX_ADDRESSES)

    def create(self, customer_id: UUID, payload: AddressInput) -> Address:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                count = connection.execute(
                    "SELECT count(*) AS total FROM customer_addresses WHERE customer_id = %s",
                    (customer_id,),
                ).fetchone()["total"]
                if count >= MAX_ADDRESSES:
                    raise Conflict(
                        f"The address book holds at most {MAX_ADDRESSES} addresses."
                    )
                # The first address is the default whether or not the caller asked,
                # so checkout always has something to preselect.
                is_default = payload.is_default or count == 0
                if is_default:
                    connection.execute(
                        """
                        UPDATE customer_addresses
                        SET is_default = false, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = %s AND is_default
                        """,
                        (customer_id,),
                    )
                row = connection.execute(
                    """
                    INSERT INTO customer_addresses(
                        address_id, customer_id, label, recipient_name, phone,
                        city, address_line, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING address_id, label, recipient_name, phone, city,
                              address_line, is_default, created_at, updated_at
                    """,
                    (
                        uuid4(),
                        customer_id,
                        payload.label,
                        payload.recipient_name,
                        payload.phone,
                        payload.city,
                        payload.address_line,
                        is_default,
                    ),
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The address store is unavailable.") from error
        return _row(row)

    def update(
        self, customer_id: UUID, address_id: UUID, payload: AddressInput
    ) -> Address:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                existing = connection.execute(
                    """
                    SELECT address_id, is_default FROM customer_addresses
                    WHERE address_id = %s AND customer_id = %s
                    FOR UPDATE
                    """,
                    (address_id, customer_id),
                ).fetchone()
                if existing is None:
                    raise ResourceNotFound("Address not found.")
                if payload.is_default and not existing["is_default"]:
                    connection.execute(
                        """
                        UPDATE customer_addresses
                        SET is_default = false, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = %s AND is_default
                        """,
                        (customer_id,),
                    )
                # Clearing the default is refused: checkout would lose its
                # preselection. Promoting another address is the supported move.
                if existing["is_default"] and not payload.is_default:
                    raise Conflict(
                        "Choose another default address instead of clearing this one."
                    )
                row = connection.execute(
                    """
                    UPDATE customer_addresses
                    SET label = %s, recipient_name = %s, phone = %s, city = %s,
                        address_line = %s, is_default = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE address_id = %s AND customer_id = %s
                    RETURNING address_id, label, recipient_name, phone, city,
                              address_line, is_default, created_at, updated_at
                    """,
                    (
                        payload.label,
                        payload.recipient_name,
                        payload.phone,
                        payload.city,
                        payload.address_line,
                        payload.is_default,
                        address_id,
                        customer_id,
                    ),
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The address store is unavailable.") from error
        return _row(row)

    def delete(self, customer_id: UUID, address_id: UUID) -> None:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                deleted = connection.execute(
                    """
                    DELETE FROM customer_addresses
                    WHERE address_id = %s AND customer_id = %s
                    RETURNING is_default
                    """,
                    (address_id, customer_id),
                ).fetchone()
                if deleted is None:
                    raise ResourceNotFound("Address not found.")
                if deleted["is_default"]:
                    # Promote the oldest survivor so checkout keeps a default.
                    connection.execute(
                        """
                        UPDATE customer_addresses
                        SET is_default = true, updated_at = CURRENT_TIMESTAMP
                        WHERE address_id = (
                            SELECT address_id FROM customer_addresses
                            WHERE customer_id = %s
                            ORDER BY created_at, address_id
                            LIMIT 1
                        )
                        """,
                        (customer_id,),
                    )
        except psycopg.Error as error:
            raise DependencyUnavailable("The address store is unavailable.") from error

    def default(self, customer_id: UUID) -> Address | None:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT address_id, label, recipient_name, phone, city,
                           address_line, is_default, created_at, updated_at
                    FROM customer_addresses
                    WHERE customer_id = %s AND is_default
                    """,
                    (customer_id,),
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The address store is unavailable.") from error
        return _row(row) if row else None


def validate_default(payload: AddressInput) -> None:
    """Guard the case the route cannot express: a blank label after trimming."""
    if not payload.label:
        raise InvalidInput("An address needs a label.")
