"""Authentication boundary for local/sandbox execution.

The project has no selected production identity provider. The current adapter maps
an opaque bearer token to `account_principals.identity_subject`; seeded tokens are
synthetic and must never be treated as production credentials.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from . import db
from .errors import DependencyUnavailable, Unauthorized


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: UUID
    account_type: str
    customer_id: UUID | None
    scopes: frozenset[str]


class Authenticator(Protocol):
    def authenticate(self, token: str) -> Principal: ...


class PostgresSandboxAuthenticator:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def authenticate(self, token: str) -> Principal:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
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
        if row is None:
            raise Unauthorized()
        return Principal(
            principal_id=row["principal_id"],
            account_type=row["account_type"],
            customer_id=row["customer_id"],
            scopes=frozenset(row["scopes"]),
        )
