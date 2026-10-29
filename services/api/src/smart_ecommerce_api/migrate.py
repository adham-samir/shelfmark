"""Ordered, checksummed PostgreSQL migration runner.

The twelve SQL files under ``database/relational/migrations`` used to be applied
only by ``docker-entrypoint-initdb.d``, which runs on an *empty* volume. A fresh
stack was therefore correct while an existing one silently lacked whatever had
been added since. This module gives both paths one mechanism.

Guarantees:

* Every migration is applied at most once, recorded in ``schema_migrations``.
* Each migration runs in its own transaction, so a failure leaves neither a
  schema change nor a version row.
* An applied file may never change. Its normalized SHA-256 is stored at apply
  time; a later edit aborts the run instead of leaving two databases that claim
  the same version with different schemas.
* Concurrent runs serialise on a PostgreSQL advisory lock.

Seeding is separate and never automatic: ``--seed`` is required, and it refuses
to run against a database that already has products.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

# A stable key so any number of API replicas starting together serialise.
ADVISORY_LOCK_KEY = 70210001

TRACKING_TABLE = "schema_migrations"

_BEGIN = re.compile(r"BEGIN\s*;", re.IGNORECASE)
_COMMIT = re.compile(r"COMMIT\s*;", re.IGNORECASE)


class MigrationError(RuntimeError):
    """A migration cannot be applied safely. Nothing was left half-applied."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    path: Path
    body: str
    checksum: str


@dataclass(slots=True)
class SeedResult:
    """A seed either ran or was skipped; both are success, only the reason differs.

    Skipping is not an error because ``docker compose up`` re-runs this service on
    every start. Writing into a populated database would be, so it never happens.
    """

    applied: list[str] = field(default_factory=list)
    skipped: str | None = None


@dataclass(slots=True)
class MigrationResult:
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.applied)


def strip_transaction(sql: str) -> str:
    """Remove an outer ``BEGIN;``/``COMMIT;`` pair, keeping everything else.

    One file (``0005_shipping_contact.sql``) is a bare set of statements while
    the rest are explicitly wrapped. The runner supplies the transaction, so the
    wrapper is redundant; leaving it would nest one inside another and make the
    commit ambiguous. Only the first and last meaningful lines are considered, so
    a ``BEGIN`` inside a function body is untouched.
    """
    lines = sql.split("\n")

    def meaningful(index: int) -> bool:
        text = lines[index].strip()
        return bool(text) and not text.startswith("--")

    indexes = [index for index in range(len(lines)) if meaningful(index)]
    if not indexes:
        return sql
    first, last = indexes[0], indexes[-1]
    if first == last:
        return sql
    if _BEGIN.fullmatch(lines[first].strip()) and _COMMIT.fullmatch(
        lines[last].strip()
    ):
        lines[first] = ""
        lines[last] = ""
    return "\n".join(lines)


def checksum(sql: str) -> str:
    """Hash the body with cosmetic differences normalised away.

    Trailing whitespace and the trailing newline vary between editors and git
    checkouts; they must not look like a semantic edit. Anything else does.
    """
    normalised = "\n".join(line.rstrip() for line in sql.split("\n")).strip() + "\n"
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def load_migrations(directory: Path) -> list[Migration]:
    """Read every ``*.sql`` file in filename order, which is the apply order."""
    if not directory.is_dir():
        raise MigrationError(f"The migrations directory does not exist: {directory}")
    files = sorted(directory.glob("*.sql"), key=lambda path: path.name)
    if not files:
        raise MigrationError(f"No migrations found in {directory}")
    migrations: list[Migration] = []
    numbers: dict[str, str] = {}
    for path in files:
        raw = path.read_text(encoding="utf-8")
        # The numeric prefix is the sequence identity: 0012_a and 0012_b would
        # both claim step twelve, and their order would depend on the suffix.
        prefix = re.match(r"(\d+)", path.stem)
        if prefix is None:
            raise MigrationError(
                f"{path.name} does not start with a numeric version prefix."
            )
        number = prefix.group(1)
        if number in numbers:
            raise MigrationError(
                f"{path.name} and {numbers[number]} share version {number}."
            )
        numbers[number] = path.name
        migrations.append(
            Migration(
                version=path.stem,
                path=path,
                body=strip_transaction(raw),
                checksum=checksum(raw),
            )
        )
    return migrations


def default_directory(name: str, variable: str) -> Path:
    """Resolve a SQL directory from the environment, then from the repo layout."""
    import os

    configured = os.getenv(variable)
    if configured:
        return Path(configured)
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / "database" / "relational" / name
        if candidate.is_dir():
            return candidate
    return Path("database") / "relational" / name


class MigrationRunner:
    def __init__(
        self,
        dsn: str,
        migrations_dir: Path | None = None,
        seeds_dir: Path | None = None,
    ) -> None:
        self._dsn = dsn
        self._migrations_dir = migrations_dir or default_directory(
            "migrations", "SMART_ECOMMERCE_MIGRATIONS_DIR"
        )
        self._seeds_dir = seeds_dir or default_directory(
            "seeds", "SMART_ECOMMERCE_SEEDS_DIR"
        )

    # ------------------------------------------------------------- inspection
    def _connect(self) -> psycopg.Connection:
        # A short-lived job owns its connection outright. Borrowing from the
        # shared pool would leave the advisory lock held by a session that the
        # pool keeps alive after this process finishes.
        return psycopg.connect(self._dsn, autocommit=True)

    @staticmethod
    def _ensure_tracking_table(connection: psycopg.Connection) -> None:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
                version text PRIMARY KEY,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
                duration_ms integer NOT NULL CHECK (duration_ms >= 0)
            )
            """
        )

    @staticmethod
    def _applied(connection: psycopg.Connection) -> dict[str, str]:
        rows = connection.execute(
            f"SELECT version, checksum FROM {TRACKING_TABLE}"
        ).fetchall()
        return {version: digest for version, digest in rows}

    def status(self) -> list[tuple[str, str | None, bool]]:
        """``(version, applied_at or None, checksum_matches)`` for every file."""
        migrations = load_migrations(self._migrations_dir)
        with self._connect() as connection:
            self._ensure_tracking_table(connection)
            rows = connection.execute(
                f"SELECT version, checksum, applied_at FROM {TRACKING_TABLE}"
            ).fetchall()
        recorded = {version: (digest, applied_at) for version, digest, applied_at in rows}
        report: list[tuple[str, str | None, bool]] = []
        for migration in migrations:
            entry = recorded.get(migration.version)
            if entry is None:
                report.append((migration.version, None, True))
            else:
                digest, applied_at = entry
                report.append(
                    (migration.version, applied_at.isoformat(), digest == migration.checksum)
                )
        return report

    # ---------------------------------------------------------------- applying
    def apply(self) -> MigrationResult:
        migrations = load_migrations(self._migrations_dir)
        started = time.monotonic()
        result = MigrationResult()
        with self._connect() as connection:
            connection.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
            try:
                self._ensure_tracking_table(connection)
                applied = self._applied(connection)
                self._reject_drift(migrations, applied)
                for migration in migrations:
                    if migration.version in applied:
                        result.skipped.append(migration.version)
                        continue
                    migration_started = time.monotonic()
                    try:
                        with connection.transaction():
                            connection.execute(migration.body)
                            elapsed = int(
                                (time.monotonic() - migration_started) * 1000
                            )
                            connection.execute(
                                f"INSERT INTO {TRACKING_TABLE}"
                                " (version, checksum, duration_ms) VALUES (%s, %s, %s)",
                                (migration.version, migration.checksum, elapsed),
                            )
                    except psycopg.Error as error:
                        raise MigrationError(
                            f"{migration.path.name} failed and was rolled back: {error}"
                        ) from error
                    result.applied.append(migration.version)
            finally:
                connection.execute(
                    "SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,)
                )
        result.duration_ms = int((time.monotonic() - started) * 1000)
        return result

    @staticmethod
    def _reject_drift(
        migrations: list[Migration], applied: dict[str, str]
    ) -> None:
        for migration in migrations:
            recorded = applied.get(migration.version)
            if recorded is not None and recorded != migration.checksum:
                raise MigrationError(
                    f"{migration.path.name} changed after it was applied. "
                    "Applied migrations are immutable; add a new numbered file."
                )

    def baseline(self) -> list[str]:
        """Record the current files as applied without running them.

        Only for a database that was built before the tracking table existed.
        It refuses an already-tracked database, and refuses an empty one, where
        the honest action is to run ``migrate`` instead.
        """
        migrations = load_migrations(self._migrations_dir)
        with self._connect() as connection:
            connection.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
            try:
                self._ensure_tracking_table(connection)
                if self._applied(connection):
                    raise MigrationError(
                        "This database is already tracked; run `migrate` instead."
                    )
                existing = connection.execute(
                    """
                    SELECT count(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name <> %s
                    """,
                    (TRACKING_TABLE,),
                ).fetchone()[0]
                if existing == 0:
                    raise MigrationError(
                        "This database is empty; run `migrate` to build it."
                    )
                with connection.transaction():
                    for migration in migrations:
                        connection.execute(
                            f"INSERT INTO {TRACKING_TABLE}"
                            " (version, checksum, duration_ms) VALUES (%s, %s, 0)",
                            (migration.version, migration.checksum),
                        )
            finally:
                connection.execute(
                    "SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,)
                )
        return [migration.version for migration in migrations]

    # ------------------------------------------------------------------ seeding
    def seed(self) -> SeedResult:
        """Apply the synthetic seed once, and never over existing products."""
        files = sorted(self._seeds_dir.glob("*.sql"), key=lambda path: path.name)
        if not files:
            raise MigrationError(f"No seed files found in {self._seeds_dir}")
        applied: list[str] = []
        with self._connect() as connection:
            connection.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
            try:
                existing = connection.execute(
                    "SELECT count(*) FROM product_registry"
                ).fetchone()[0]
                if existing:
                    return SeedResult(
                        skipped=f"{existing} products already present; left untouched"
                    )
                for path in files:
                    raw = path.read_text(encoding="utf-8")
                    try:
                        with connection.transaction():
                            connection.execute(strip_transaction(raw))
                    except psycopg.Error as error:
                        raise MigrationError(
                            f"{path.name} failed and was rolled back: {error}"
                        ) from error
                    applied.append(path.stem)
            finally:
                connection.execute(
                    "SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,)
                )
        return SeedResult(applied=applied)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m smart_ecommerce_api.migrate",
        description="Apply ordered, checksummed PostgreSQL migrations.",
    )
    parser.add_argument(
        "--status", action="store_true", help="Report what is applied, then exit."
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Record existing files as applied without running them.",
    )
    parser.add_argument(
        "--seed", action="store_true", help="Apply the synthetic seed after migrating."
    )
    arguments = parser.parse_args(argv)

    from .config import Settings

    settings = Settings.from_environment()
    runner = MigrationRunner(settings.postgres_dsn)

    try:
        if arguments.status:
            for version, applied_at, matches in runner.status():
                if applied_at is None:
                    state = "pending"
                elif matches:
                    state = f"applied {applied_at}"
                else:
                    state = "CHANGED since it was applied"
                print(f"{version:<40} {state}")
            return 0

        if arguments.baseline:
            recorded = runner.baseline()
            print(f"baselined {len(recorded)} migrations without running them")
            return 0

        result = runner.apply()
        for version in result.applied:
            print(f"applied  {version}")
        print(
            f"{len(result.applied)} applied, {len(result.skipped)} already applied "
            f"({result.duration_ms} ms)"
        )
        if arguments.seed:
            seeded = runner.seed()
            for name in seeded.applied:
                print(f"seeded   {name}")
            if seeded.skipped:
                print(f"seed skipped: {seeded.skipped}")
        return 0
    except MigrationError as error:
        print(f"migration failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
