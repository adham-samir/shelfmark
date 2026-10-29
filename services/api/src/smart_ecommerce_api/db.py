"""Bounded PostgreSQL connection pool shared by every store.

Every API request used to open its own server connection. Under the DEC-014
demonstration workload (100 concurrent sessions) that exhausted PostgreSQL's
default 100 connection slots and turned otherwise valid reads into typed 503
responses. Stores now borrow from one process-wide pool per DSN, so concurrency
is bounded by ``SMART_ECOMMERCE_POSTGRES_POOL_SIZE`` instead of by the database
server limit.

The helper mirrors the semantics of ``psycopg.connect(...)`` as a context
manager: the transaction commits on a clean exit, rolls back on error, and the
connection returns to the pool either way. ``row_factory`` is set per borrow so
callers keep the exact row shape they expect.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool, PoolTimeout

DEFAULT_POOL_SIZE = 48
ACQUIRE_TIMEOUT_SECONDS = 10.0

_pools: dict[str, ConnectionPool] = {}
_guard = threading.Lock()


def _pool_size() -> int:
    try:
        size = int(os.getenv("SMART_ECOMMERCE_POSTGRES_POOL_SIZE", ""))
    except ValueError:
        return DEFAULT_POOL_SIZE
    return size if size > 0 else DEFAULT_POOL_SIZE


def _pool(dsn: str) -> ConnectionPool:
    with _guard:
        pool = _pools.get(dsn)
        if pool is None:
            pool = ConnectionPool(
                dsn,
                min_size=0,
                max_size=_pool_size(),
                timeout=ACQUIRE_TIMEOUT_SECONDS,
                open=True,
                name="smart-ecommerce",
            )
            _pools[dsn] = pool
        return pool


@contextmanager
def connection(
    dsn: str, *, row_factory: Any = None
) -> Iterator[psycopg.Connection[Any]]:
    """Borrow a pooled connection for one transaction."""
    try:
        with _pool(dsn).connection() as borrowed:
            previous = borrowed.row_factory
            if row_factory is not None:
                borrowed.row_factory = row_factory
            try:
                yield borrowed
            finally:
                borrowed.row_factory = previous
    except PoolTimeout as error:
        # Stores map psycopg errors to their own typed dependency failures, so the
        # pool reports exhaustion in the same shape as a refused connection.
        raise psycopg.OperationalError(
            "The database connection could not be acquired."
        ) from error


def close_pools() -> None:
    """Close every pool. One-shot jobs call this so they exit without a
    finalization warning from the pool's worker threads."""
    with _guard:
        pools = list(_pools.values())
        _pools.clear()
    for pool in pools:
        pool.close()
