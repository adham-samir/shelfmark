"""Demo identity: credentials, sessions, account profile, and order history.

This is an explicit demonstration harness, not a production identity provider.
Passwords are argon2id hashes of values printed in the user manual; session
tokens are random 32-byte values stored only as SHA-256 digests. The legacy
`account_principals.identity_subject` bearer path is retained so existing
sandbox tests and scripts keep working while the storefront moves to sessions.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import Field
from pwdlib import PasswordHash

from . import db
from .auth import Principal
from .errors import (
    Conflict,
    DependencyUnavailable,
    InvalidInput,
    TooManyRequests,
    Unauthorized,
)
from .models import StrictModel

Surface = Literal["customer", "operator"]
SESSION_TTL = timedelta(days=7)
PASSWORD_HASH = PasswordHash.recommended()
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterInput(StrictModel):
    email: Annotated[str, Field(min_length=5, max_length=254, pattern=EMAIL_PATTERN)]
    display_name: Annotated[str, Field(min_length=2, max_length=120)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    preferred_locale: Literal["ar", "en"] = "ar"


class LoginInput(StrictModel):
    email: Annotated[str, Field(min_length=5, max_length=254)]
    password: Annotated[str, Field(min_length=1, max_length=128)]
    surface: Surface = "customer"


class AccountUpdate(StrictModel):
    display_name: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    preferred_locale: Literal["ar", "en"] | None = None


class AccountProfile(StrictModel):
    customer_id: UUID
    email: str
    display_name: str
    preferred_locale: Literal["ar", "en"]
    member_since: datetime
    order_count: int


class AccountView(StrictModel):
    principal_id: UUID
    account_type: Literal["customer", "backoffice"]
    customer_id: UUID | None
    scopes: list[str]
    profile: AccountProfile | None = None


class AuthSession(StrictModel):
    token: str
    surface: Surface
    expires_at: datetime
    account: AccountView


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _profile_row(row: dict) -> AccountProfile:
    return AccountProfile(
        customer_id=row["customer_id"],
        email=row["email"],
        display_name=row["display_name"],
        preferred_locale=row["preferred_locale"],
        member_since=row["created_at"],
        order_count=row["order_count"],
    )


PROFILE_SELECT = """
    SELECT c.customer_id, c.email, c.display_name, c.preferred_locale, c.created_at,
           (SELECT count(*) FROM orders o WHERE o.customer_id = c.customer_id) AS order_count
    FROM customers c
    WHERE c.customer_id = %s
"""


class IdentityStore:
    """Credential, session, account, and order-history store."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    # ---------------------------------------------------------------- sessions
    def _issue_session(
        self, connection: psycopg.Connection, principal_id: UUID, surface: Surface
    ) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = _utcnow() + SESSION_TTL
        connection.execute(
            """
            INSERT INTO sessions (session_id, principal_id, token_hash, surface, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (uuid4(), principal_id, hash_token(token), surface, expires_at),
        )
        return token, expires_at

    def authenticate(self, token: str) -> Principal:
        """Resolve a session token, falling back to the legacy sandbox subject."""
        digest = hash_token(token)
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT p.principal_id, p.account_type, p.customer_id,
                           COALESCE(array_agg(sc.scope) FILTER (WHERE sc.scope IS NOT NULL), '{}') AS scopes,
                           se.session_id, se.expires_at
                    FROM sessions se
                    JOIN account_principals p USING (principal_id)
                    LEFT JOIN principal_scopes sc ON sc.principal_id = p.principal_id
                    WHERE se.token_hash = %s AND se.revoked_at IS NULL
                      AND se.expires_at > CURRENT_TIMESTAMP AND p.enabled
                    GROUP BY p.principal_id, se.session_id, se.expires_at
                    """,
                    (digest,),
                ).fetchone()
                if row is not None:
                    connection.execute(
                        """
                        UPDATE sessions
                        SET last_seen_at = CURRENT_TIMESTAMP,
                            expires_at = CURRENT_TIMESTAMP + %s
                        WHERE session_id = %s
                        """,
                        (SESSION_TTL, row["session_id"]),
                    )
                    return Principal(
                        principal_id=row["principal_id"],
                        account_type=row["account_type"],
                        customer_id=row["customer_id"],
                        scopes=frozenset(row["scopes"]),
                    )
                legacy = connection.execute(
                    """
                    SELECT p.principal_id, p.account_type, p.customer_id,
                           COALESCE(array_agg(s.scope) FILTER (WHERE s.scope IS NOT NULL), '{}') AS scopes
                    FROM account_principals p
                    LEFT JOIN principal_scopes s USING (principal_id)
                    WHERE p.identity_subject = %s AND p.enabled
                    GROUP BY p.principal_id
                    """,
                    (token,),
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error
        if legacy is None:
            raise Unauthorized()
        return Principal(
            principal_id=legacy["principal_id"],
            account_type=legacy["account_type"],
            customer_id=legacy["customer_id"],
            scopes=frozenset(legacy["scopes"]),
        )

    def revoke(self, token: str) -> None:
        try:
            with db.connection(self._dsn) as connection:
                connection.execute(
                    "UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = %s",
                    (hash_token(token),),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error

    # ------------------------------------------------------------------- login
    def login(self, credentials: LoginInput) -> AuthSession:
        email = credentials.email.strip().lower()
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT p.principal_id, p.account_type, p.customer_id, p.enabled,
                           COALESCE(array_agg(s.scope) FILTER (WHERE s.scope IS NOT NULL), '{}') AS scopes,
                           c.password_hash
                    FROM account_principals p
                    LEFT JOIN customers cu ON cu.customer_id = p.customer_id
                    JOIN account_credentials c ON c.principal_id = p.principal_id
                    LEFT JOIN principal_scopes s ON s.principal_id = p.principal_id
                    WHERE COALESCE(cu.email, p.login_email) = %s
                    GROUP BY p.principal_id, c.password_hash
                    """,
                    (email,),
                ).fetchone()
                # Operators authenticate with the same form; look them up by the
                # demo identity label when there is no customer email match.
                if row is None and credentials.surface == "operator":
                    row = connection.execute(
                        """
                        SELECT p.principal_id, p.account_type, p.customer_id, p.enabled,
                               COALESCE(array_agg(s.scope) FILTER (WHERE s.scope IS NOT NULL), '{}') AS scopes,
                               c.password_hash
                        FROM account_principals p
                        JOIN account_credentials c ON c.principal_id = p.principal_id
                        LEFT JOIN principal_scopes s ON s.principal_id = p.principal_id
                        WHERE p.account_type = 'backoffice' AND p.identity_subject = %s
                        GROUP BY p.principal_id, c.password_hash
                        """,
                        (email,),
                    ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error

        if row is None or not row["enabled"]:
            raise Unauthorized()
        if not PASSWORD_HASH.verify(credentials.password, row["password_hash"]):
            raise Unauthorized()
        expected_type = "backoffice" if credentials.surface == "operator" else "customer"
        if row["account_type"] != expected_type:
            raise Unauthorized()

        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                token, expires_at = self._issue_session(
                    connection, row["principal_id"], credentials.surface
                )
                profile = None
                if row["customer_id"] is not None:
                    candidate = connection.execute(
                        PROFILE_SELECT, (row["customer_id"],)
                    ).fetchone()
                    if candidate is not None:
                        profile = _profile_row(candidate)
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error

        return AuthSession(
            token=token,
            surface=credentials.surface,
            expires_at=expires_at,
            account=AccountView(
                principal_id=row["principal_id"],
                account_type=row["account_type"],
                customer_id=row["customer_id"],
                scopes=sorted(row["scopes"]),
                profile=profile,
            ),
        )

    # ---------------------------------------------------------------- register
    def register(self, registration: RegisterInput) -> AuthSession:
        email = registration.email.strip().lower()
        display_name = registration.display_name.strip()
        if not display_name:
            raise InvalidInput("A display name is required.")
        if registration.password.strip().lower() in {
            "password",
            "password1",
            "12345678",
            "qwertyui",
        }:
            raise InvalidInput("Choose a less common demonstration password.")

        customer_id = uuid4()
        principal_id = uuid4()
        password_hash = PASSWORD_HASH.hash(registration.password)
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                connection.execute(
                    """
                    INSERT INTO customers (customer_id, email, display_name, preferred_locale)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (customer_id, email, display_name, registration.preferred_locale),
                )
                connection.execute(
                    """
                    INSERT INTO account_principals
                        (principal_id, identity_subject, account_type, customer_id)
                    VALUES (%s, %s, 'customer', %s)
                    """,
                    (principal_id, f"demo-customer-{customer_id}", customer_id),
                )
                connection.execute(
                    "INSERT INTO account_credentials (principal_id, password_hash) VALUES (%s, %s)",
                    (principal_id, password_hash),
                )
                token, expires_at = self._issue_session(
                    connection, principal_id, "customer"
                )
                profile = connection.execute(
                    PROFILE_SELECT, (customer_id,)
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise Conflict("An account with that email already exists.") from error
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error

        return AuthSession(
            token=token,
            surface="customer",
            expires_at=expires_at,
            account=AccountView(
                principal_id=principal_id,
                account_type="customer",
                customer_id=customer_id,
                scopes=[],
                profile=_profile_row(profile),
            ),
        )

    # ----------------------------------------------------------------- account
    def profile(self, customer_id: UUID) -> AccountProfile:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(PROFILE_SELECT, (customer_id,)).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error
        if row is None:
            raise Unauthorized()
        return _profile_row(row)

    def update_profile(
        self, customer_id: UUID, update: AccountUpdate
    ) -> AccountProfile:
        fields: list[str] = []
        values: list[object] = []
        if update.display_name is not None:
            name = update.display_name.strip()
            if len(name) < 2:
                raise InvalidInput("A display name needs at least two characters.")
            fields.append("display_name = %s")
            values.append(name)
        if update.preferred_locale is not None:
            fields.append("preferred_locale = %s")
            values.append(update.preferred_locale)
        if not fields:
            return self.profile(customer_id)
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    f"""
                    UPDATE customers SET {", ".join(fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = %s
                    RETURNING customer_id
                    """,
                    (*values, customer_id),
                ).fetchone()
                if row is None:
                    raise Unauthorized()
                profile = connection.execute(
                    PROFILE_SELECT, (customer_id,)
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The identity store is unavailable.") from error
        return _profile_row(profile)

    def view(self, principal: Principal) -> AccountView:
        profile = (
            self.profile(principal.customer_id)
            if principal.customer_id is not None
            else None
        )
        return AccountView(
            principal_id=principal.principal_id,
            account_type=principal.account_type,
            customer_id=principal.customer_id,
            scopes=sorted(principal.scopes),
            profile=profile,
        )


class LoginThrottle:
    """Process-local login rate limit: 10 failures per key in five minutes."""

    def __init__(self, limit: int = 10, window_seconds: int = 300) -> None:
        self._limit = limit
        self._window = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._guard = threading.Lock()

    def _recent(self, key: str) -> list[float]:
        cutoff = time.monotonic() - self._window
        entries = [stamp for stamp in self._failures.get(key, []) if stamp > cutoff]
        if entries:
            self._failures[key] = entries
        else:
            self._failures.pop(key, None)
        return entries

    def check(self, key: str) -> None:
        with self._guard:
            if len(self._recent(key)) >= self._limit:
                raise TooManyRequests()

    def failure(self, key: str) -> None:
        with self._guard:
            entries = self._recent(key)
            entries.append(time.monotonic())
            self._failures[key] = entries

    def success(self, key: str) -> None:
        with self._guard:
            self._failures.pop(key, None)
