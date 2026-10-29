"""Migration runner: pure parsing rules, plus database behaviour when available.

The parsing tests always run. The database tests need a disposable PostgreSQL
instance and are skipped unless ``SMART_ECOMMERCE_TEST_POSTGRES_DSN`` is set, so
the fast suite stays free of external services.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from smart_ecommerce_api.migrate import (
    MigrationError,
    MigrationRunner,
    checksum,
    load_migrations,
    strip_transaction,
)

ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = ROOT / "database" / "relational" / "migrations"
SEEDS = ROOT / "database" / "relational" / "seeds"


# --------------------------------------------------------------------- parsing
def test_strip_removes_the_outer_transaction_pair():
    body = "BEGIN;\n\nCREATE TABLE t (id int);\n\nCOMMIT;\n"
    stripped = strip_transaction(body)
    assert "BEGIN" not in stripped
    assert "COMMIT" not in stripped
    assert "CREATE TABLE t (id int);" in stripped


def test_strip_leaves_an_unwrapped_migration_alone():
    # 0005_shipping_contact.sql is the only file with no transaction wrapper.
    body = "-- comment\nALTER TABLE orders ADD COLUMN x text;\n"
    assert strip_transaction(body) == body


def test_strip_ignores_a_begin_inside_the_body():
    body = (
        "BEGIN;\n"
        "CREATE FUNCTION f() RETURNS void AS $$\n"
        "BEGIN\n"
        "  PERFORM 1;\n"
        "END\n"
        "$$ LANGUAGE plpgsql;\n"
        "COMMIT;\n"
    )
    stripped = strip_transaction(body)
    # The outer pair is gone; the function's inner BEGIN/END survives.
    assert stripped.strip().startswith("CREATE FUNCTION")
    assert "BEGIN\n  PERFORM 1;" in stripped
    assert not stripped.rstrip().endswith("COMMIT;")


def test_strip_handles_a_comment_only_prefix():
    body = "-- a\n-- b\nBEGIN;\nSELECT 1;\nCOMMIT;\n"
    stripped = strip_transaction(body)
    assert "-- a" in stripped
    assert "SELECT 1;" in stripped
    assert "COMMIT" not in stripped


def test_checksum_ignores_cosmetic_whitespace_but_not_content():
    base = "BEGIN;\nSELECT 1;\nCOMMIT;\n"
    padded = "BEGIN;   \nSELECT 1;\nCOMMIT;\n\n\n"
    assert checksum(base) == checksum(padded)
    assert checksum(base) != checksum("BEGIN;\nSELECT 2;\nCOMMIT;\n")


def test_real_migrations_load_in_filename_order():
    migrations = load_migrations(MIGRATIONS)
    versions = [migration.version for migration in migrations]
    assert versions == sorted(versions)
    assert versions[0].startswith("0001_")
    assert versions[-1].startswith("0012_")
    # Every file must be executable as a single statement batch.
    for migration in migrations:
        assert migration.body.strip(), migration.version
        assert "BEGIN;" not in migration.body.split("\n")[0], migration.version


def test_missing_directory_is_a_typed_error():
    with pytest.raises(MigrationError):
        load_migrations(ROOT / "does-not-exist")


def test_duplicate_versions_are_rejected(tmp_path):
    (tmp_path / "0001_a.sql").write_text("SELECT 1;")
    (tmp_path / "0001_b.sql").write_text("SELECT 2;")
    with pytest.raises(MigrationError, match="share version 0001"):
        load_migrations(tmp_path)


# -------------------------------------------------------------------- database
DSN = os.getenv("SMART_ECOMMERCE_TEST_POSTGRES_DSN")

needs_database = pytest.mark.skipif(
    not DSN, reason="SMART_ECOMMERCE_TEST_POSTGRES_DSN is not set"
)


class _ScratchDatabase:
    """A throwaway database per test, so migrations start from nothing."""

    def __init__(self) -> None:
        self.name = f"migrate_test_{uuid.uuid4().hex[:10]}"

    def __enter__(self) -> str:
        import psycopg
        from psycopg.conninfo import make_conninfo

        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'CREATE DATABASE "{self.name}"')
        return make_conninfo(DSN, dbname=self.name)

    def __exit__(self, *_exc) -> None:
        import psycopg

        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{self.name}" WITH (FORCE)')


@needs_database
def test_apply_is_idempotent_and_records_versions():
    import psycopg

    with _ScratchDatabase() as dsn:
        runner = MigrationRunner(dsn, MIGRATIONS, SEEDS)
        first = runner.apply()
        assert len(first.applied) == len(load_migrations(MIGRATIONS))
        assert first.skipped == []

        second = runner.apply()
        assert second.applied == []
        assert len(second.skipped) == len(load_migrations(MIGRATIONS))

        report = runner.status()
        assert all(applied_at is not None for _, applied_at, _ in report)
        assert all(matches for _, _, matches in report)

        with psycopg.connect(dsn) as connection:
            tables = connection.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ).fetchone()[0]
        # Twelve migrations produce the documented 30-table schema, plus the
        # runner's own tracking table.
        assert tables == 31


@needs_database
def test_an_edited_migration_aborts_before_anything_is_applied(tmp_path):
    with _ScratchDatabase() as dsn:
        copy = tmp_path / "migrations"
        copy.mkdir()
        (copy / "0001_one.sql").write_text("CREATE TABLE one (id int);")
        MigrationRunner(dsn, copy, SEEDS).apply()

        # Same version, different content: the run must refuse, not silently pass.
        (copy / "0001_one.sql").write_text("CREATE TABLE one (id int, extra int);")
        with pytest.raises(MigrationError, match="changed after it was applied"):
            MigrationRunner(dsn, copy, SEEDS).apply()


@needs_database
def test_a_failing_migration_leaves_no_partial_state(tmp_path):
    import psycopg

    with _ScratchDatabase() as dsn:
        copy = tmp_path / "migrations"
        copy.mkdir()
        (copy / "0001_good.sql").write_text("CREATE TABLE good (id int);")
        (copy / "0002_bad.sql").write_text("CREATE TABLE bad (id int);\nSELECT 1/0;")
        with pytest.raises(MigrationError, match="rolled back"):
            MigrationRunner(dsn, copy, SEEDS).apply()

        with psycopg.connect(dsn) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ).fetchall()
            }
            versions = {
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }
        assert "good" in tables
        assert "bad" not in tables
        assert versions == {"0001_good"}


@needs_database
def test_baseline_records_without_running_and_refuses_the_wrong_cases():
    import psycopg

    with _ScratchDatabase() as dsn:
        runner = MigrationRunner(dsn, MIGRATIONS, SEEDS)

        # Nothing exists yet: the honest action is to build it, not to adopt it.
        with pytest.raises(MigrationError, match="empty"):
            runner.baseline()

        # Simulate a database built before tracking existed.
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute("CREATE TABLE product_registry (product_id uuid)")
        recorded = runner.baseline()
        assert len(recorded) == len(load_migrations(MIGRATIONS))

        # It is tracked now; baselining again must refuse.
        with pytest.raises(MigrationError, match="already tracked"):
            runner.baseline()
        # And a tracked database applies nothing.
        assert runner.apply().applied == []


@needs_database
def test_seed_runs_once_and_refuses_a_populated_database():
    import psycopg

    with _ScratchDatabase() as dsn:
        runner = MigrationRunner(dsn, MIGRATIONS, SEEDS)
        runner.apply()
        first = runner.seed()
        assert first.applied == ["0001_synthetic_demo"]
        assert first.skipped is None

        with psycopg.connect(dsn) as connection:
            products = connection.execute(
                "SELECT count(*) FROM product_registry"
            ).fetchone()[0]
        assert products == 13

        # A second run (which compose performs on every `up`) writes nothing and
        # still succeeds, because failing here would block the API from starting.
        again = runner.seed()
        assert again.applied == []
        assert "already present" in (again.skipped or "")
        with psycopg.connect(dsn) as connection:
            assert (
                connection.execute("SELECT count(*) FROM product_registry").fetchone()[0]
                == 13
            )
