"""Exercise real database constraints in disposable containers without host ports."""

from pathlib import Path
import subprocess
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ID = "10000000-0000-4000-8000-000000000001"


def run(*args, stdin=None, check=True, timeout=120):
    result = subprocess.run(
        args, input=stdin, text=True, capture_output=True, check=False, timeout=timeout
    )
    if check and result.returncode != 0:
        # mongosh can include a huge bundled source line in exception output.
        diagnostic = "\n".join(
            line if len(line) <= 1000 else line[:300] + " ... " + line[-300:]
            for line in (result.stdout + "\n" + result.stderr).splitlines()[-20:]
        )
        raise RuntimeError(f"{args[0]} failed ({result.returncode}):\n{diagnostic}")
    return result


class DatabaseFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.containers = []
        cls.addClassCleanup(cls.stop_containers)
        task_id = uuid.uuid4().hex[:12]
        cls.postgres = f"smart-ecommerce-schema-pg-{task_id}"
        cls.mongo = f"smart-ecommerce-schema-mongo-{task_id}"
        for name, image, env in [
            (cls.postgres, "postgres:18.6", ["-e", "POSTGRES_PASSWORD=ephemeral-schema-test", "-e", "PGPASSWORD=ephemeral-schema-test"]),
            (cls.mongo, "mongo:8.2", []),
        ]:
            print(f"\nStarting isolated schema checks with {image}...", flush=True)
            # Register before starting so a failure still attempts only this task's cleanup.
            cls.containers.append(name)
            run("docker", "run", "--detach", "--network", "none", "--name", name,
                "--mount", f"type=bind,source={ROOT},target=/workspace,readonly",
                "--workdir", "/workspace", *env, image, timeout=300)

        for name, command in [
            (cls.postgres, ["pg_isready", "-h", "127.0.0.1", "-U", "postgres"]),
            (cls.mongo, ["mongosh", "--quiet", "--eval", "quit(db.adminCommand({ping: 1}).ok ? 0 : 1)"]),
        ]:
            # A cold container on a small CI runner can take longer than a local
            # start, so allow three minutes before giving up.
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if run("docker", "exec", name, *command, check=False, timeout=10).returncode == 0:
                    break
                time.sleep(0.5)
            else:
                logs = run("docker", "logs", "--tail", "20", name, check=False, timeout=20)
                raise RuntimeError(
                    f"Database readiness failed: {name}\n{logs.stdout}\n{logs.stderr}"
                )

        for migration in sorted((ROOT / "database/relational/migrations").glob("*.sql")):
            cls.sql(migration.read_text())
        cls.setup_catalog()
        pg_version = cls.sql("SHOW server_version;").stdout.strip()
        mongo_version = cls.js("print(await db.version());").stdout.strip()
        print(f"\nDatabase versions: PostgreSQL {pg_version}; MongoDB {mongo_version}", flush=True)

    @classmethod
    def stop_containers(cls):
        for name in cls.containers:
            # Force-remove so a crashed container's log is still capturable before
            # cleanup, and nothing lingers between runs.
            run("docker", "rm", "--force", name, check=False, timeout=30)

    @classmethod
    def sql(cls, query, check=True):
        return run("docker", "exec", "-i", cls.postgres, "psql", "-h", "127.0.0.1",
                   "-U", "postgres", "-d", "postgres", "-X", "-A", "-t",
                   "-v", "ON_ERROR_STOP=1", stdin=query, check=check)

    @classmethod
    def js(cls, code):
        return run("docker", "exec", cls.mongo, "mongosh", "--quiet",
                   "mongodb://127.0.0.1:27017/schema_test", "--eval",
                   "(async () => { const checks = require('node:assert/strict');\n" + code
                   + "\n})().catch(error => { print(error.stack); quit(1); });")

    @classmethod
    def js_in_database(cls, database, code):
        return run("docker", "exec", cls.mongo, "mongosh", "--quiet",
                   f"mongodb://127.0.0.1:27017/{database}", "--eval",
                   "(async () => { const checks = require('node:assert/strict');\n" + code
                   + "\n})().catch(error => { print(error.stack); quit(1); });")

    @classmethod
    def setup_catalog(cls):
        return run("docker", "exec", cls.mongo, "mongosh", "--quiet",
                   "mongodb://127.0.0.1:27017/schema_test", "--file", "database/catalog/setup.js")

    def assert_sql_rejected(self, query, expected):
        result = self.sql(f"BEGIN;\n{query}\nROLLBACK;", check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected, result.stderr)

    def test_exact_price_and_generated_available_stock(self):
        result = self.sql(f"""
            BEGIN;
            INSERT INTO product_registry(product_id) VALUES ('{PRODUCT_ID}');
            INSERT INTO product_prices(product_id, amount, currency)
              VALUES ('{PRODUCT_ID}', 12.123456, 'XXX');
            INSERT INTO inventory_balances(product_id, on_hand, reserved)
              VALUES ('{PRODUCT_ID}', 10, 3);
            SELECT amount, currency, available FROM product_prices JOIN inventory_balances USING (product_id);
            UPDATE inventory_balances SET reserved = 5 WHERE product_id = '{PRODUCT_ID}';
            SELECT available FROM inventory_balances WHERE product_id = '{PRODUCT_ID}';
            ROLLBACK;
        """)
        self.assertIn("12.123456|XXX|7", result.stdout)
        self.assertIn("\n5\n", result.stdout)

    def test_invalid_prices_and_orphan_references_are_rejected(self):
        registry = f"INSERT INTO product_registry(product_id) VALUES ('{PRODUCT_ID}');"
        for amount in ["-0.01", "'NaN'", "'Infinity'"]:
            with self.subTest(amount=amount):
                result = self.sql(f"BEGIN; {registry} INSERT INTO product_prices(product_id, amount, currency) VALUES ('{PRODUCT_ID}', {amount}, 'XXX'); ROLLBACK;", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue("check constraint" in result.stderr or "numeric field overflow" in result.stderr, result.stderr)
        self.assert_sql_rejected(f"INSERT INTO product_prices(product_id, amount, currency) VALUES ('{PRODUCT_ID}', 10, 'XXX');", "foreign key constraint")
        self.assert_sql_rejected(f"{registry} INSERT INTO product_prices(product_id, amount, currency) VALUES ('{PRODUCT_ID}', 10, 'xx');", "check constraint")
        self.assert_sql_rejected(f"{registry} INSERT INTO product_prices(product_id, amount) VALUES ('{PRODUCT_ID}', 10);", "not-null constraint")

    def test_invalid_stock_and_duplicate_identity_are_rejected(self):
        registry = f"INSERT INTO product_registry(product_id) VALUES ('{PRODUCT_ID}');"
        for on_hand, reserved in [(-1, 0), (10, -1), (2, 3)]:
            with self.subTest(on_hand=on_hand, reserved=reserved):
                self.assert_sql_rejected(f"{registry} INSERT INTO inventory_balances(product_id, on_hand, reserved) VALUES ('{PRODUCT_ID}', {on_hand}, {reserved});", "check constraint")
        self.assert_sql_rejected(registry + registry, "duplicate key")
        self.assert_sql_rejected(f"INSERT INTO product_registry(product_id, lifecycle) VALUES ('{PRODUCT_ID}', 'invented');", "check constraint")

    def test_migration_repeat_fails_without_partial_changes(self):
        result = self.sql((ROOT / "database/relational/migrations/0001_product_foundation.sql").read_text(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('relation "product_registry" already exists', result.stderr)
        result = self.sql("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        self.assertEqual(result.stdout.strip(), "30")

    def test_commerce_identity_cart_risk_and_reorder_constraints(self):
        customer = "21000000-0000-4000-8000-000000000001"
        principal = "31000000-0000-4000-8000-000000000001"
        cart_one = "41000000-0000-4000-8000-000000000001"
        cart_two = "41000000-0000-4000-8000-000000000002"
        self.assert_sql_rejected(
            f"INSERT INTO account_principals(principal_id, identity_subject, account_type) "
            f"VALUES ('{principal}', 'invalid-customer', 'customer');",
            "check constraint",
        )
        self.assert_sql_rejected(
            "BEGIN; "
            "INSERT INTO product_registry(product_id, lifecycle) VALUES ('10000000-0000-4000-8000-000000000099', 'active'); "
            "INSERT INTO model_versions(model_version_id, module, version_label, dataset_snapshot_id, artifact_reference, framework) "
            "VALUES ('73000000-0000-4000-8000-000000000099', 'forecast', 'fixture-v1', 'fixture', 'fixture.joblib', 'scikit-learn'); "
            "INSERT INTO demand_forecasts(forecast_id, product_id, model_version_id, horizon_start, horizon_end, predicted_quantity) "
            "VALUES ('72000000-0000-4000-8000-000000000099', '10000000-0000-4000-8000-000000000099', "
            "'73000000-0000-4000-8000-000000000099', CURRENT_DATE, CURRENT_DATE + 13, 10); "
            "INSERT INTO reorder_records(reorder_id, product_id, forecast_id, idempotency_key, quantity, status, policy_snapshot) "
            "VALUES ('71000000-0000-4000-8000-000000000099', '10000000-0000-4000-8000-000000000099', "
            "'72000000-0000-4000-8000-000000000099', 'bad-policy', 1, 'created', '[]'::jsonb); "
            "ROLLBACK;",
            "check constraint",
        )
        self.assert_sql_rejected(
            f"INSERT INTO customers(customer_id, email, display_name) VALUES "
            f"('{customer}', 'synthetic@example.invalid', 'Synthetic'); "
            f"INSERT INTO carts(cart_id, customer_id) VALUES ('{cart_one}', '{customer}'); "
            f"INSERT INTO carts(cart_id, customer_id) VALUES ('{cart_two}', '{customer}');",
            "duplicate key",
        )

        transaction = "51000000-0000-4000-8000-000000000001"
        assessment = "61000000-0000-4000-8000-000000000001"
        order = "71000000-0000-4000-8000-000000000001"
        self.assert_sql_rejected(
            f"INSERT INTO customers(customer_id, email, display_name) VALUES "
            f"('{customer}', 'risk@example.invalid', 'Risk fixture'); "
            f"INSERT INTO orders(order_id, customer_id, status, subtotal) VALUES "
            f"('{order}', '{customer}', 'pending_risk', 100); "
            f"INSERT INTO payment_transactions(transaction_id, order_id, provider_reference, token_reference, amount, currency, status) VALUES "
            f"('{transaction}', '{order}', 'provider-fixture', 'token-fixture', 100, 'EGP', 'prepared'); "
            f"INSERT INTO risk_assessments(assessment_id, transaction_id, score, outcome) VALUES "
            f"('{assessment}', '{transaction}', 1.1, 'review');",
            "check constraint",
        )

    def test_order_adjustments_require_operator_actor_and_kind_amount_shape(self):
        customer = "21000000-0000-4000-8000-0000000000a1"
        order = "71000000-0000-4000-8000-0000000000a1"
        principal = "31000000-0000-4000-8000-0000000000a1"
        fixture = (
            f"INSERT INTO customers(customer_id, email, display_name) "
            f"VALUES ('{customer}', 'adjustment@example.invalid', 'Adjustment fixture'); "
            f"INSERT INTO orders(order_id, customer_id, status, subtotal) "
            f"VALUES ('{order}', '{customer}', 'confirmed', 100); "
            f"INSERT INTO account_principals(principal_id, identity_subject, account_type) "
            f"VALUES ('{principal}', 'adjustment-operator', 'backoffice'); "
        )
        # A cancellation row cannot carry money.
        self.assert_sql_rejected(
            fixture
            + "INSERT INTO order_adjustments(adjustment_id, order_id, kind, amount, reason, actor_principal_id) "
            "VALUES ('75000000-0000-4000-8000-0000000000a1', "
            f"'{order}', 'cancellation', 10, 'Should be zero', '{principal}');",
            "check constraint",
        )
        # A refund row must carry a positive amount.
        self.assert_sql_rejected(
            fixture
            + "INSERT INTO order_adjustments(adjustment_id, order_id, kind, amount, reason, actor_principal_id) "
            "VALUES ('75000000-0000-4000-8000-0000000000a2', "
            f"'{order}', 'refund', 0, 'Should be positive', '{principal}');",
            "check constraint",
        )
        # Every adjustment needs an accountable operator.
        self.assert_sql_rejected(
            fixture
            + "INSERT INTO order_adjustments(adjustment_id, order_id, kind, amount, reason) "
            "VALUES ('75000000-0000-4000-8000-0000000000a3', "
            f"'{order}', 'refund', 5, 'No actor');",
            "not-null",
        )
        # orders:write is now an accepted capability grant.
        result = self.sql(
            "BEGIN; "
            f"INSERT INTO account_principals(principal_id, identity_subject, account_type) "
            f"VALUES ('{principal}', 'adjustment-operator-2', 'backoffice'); "
            f"INSERT INTO principal_scopes(principal_id, scope) VALUES ('{principal}', 'orders:write'); "
            "SELECT scope FROM principal_scopes WHERE principal_id = '" + principal + "'; "
            "ROLLBACK;"
        )
        self.assertIn("orders:write", result.stdout)
        self.assert_sql_rejected(
            "BEGIN; "
            f"INSERT INTO account_principals(principal_id, identity_subject, account_type) "
            f"VALUES ('{principal}', 'adjustment-operator-3', 'backoffice'); "
            f"INSERT INTO principal_scopes(principal_id, scope) VALUES ('{principal}', 'orders:delete'); "
            "ROLLBACK;",
            "check constraint",
        )

    def test_customer_address_book_default_and_ownership_rules(self):
        customer = "21000000-0000-4000-8000-0000000000b1"
        other = "21000000-0000-4000-8000-0000000000b2"
        fixture = (
            f"INSERT INTO customers(customer_id, email, display_name) "
            f"VALUES ('{customer}', 'address@example.invalid', 'Address fixture'); "
            f"INSERT INTO customers(customer_id, email, display_name) "
            f"VALUES ('{other}', 'address-other@example.invalid', 'Other fixture'); "
        )
        # At most one default address per customer.
        self.assert_sql_rejected(
            fixture
            + "INSERT INTO customer_addresses(address_id, customer_id, label, recipient_name, phone, city, address_line, is_default) "
            "VALUES ('76000000-0000-4000-8000-0000000000b1', "
            f"'{customer}', 'Home', 'Synthetic', '+201000000001', 'Cairo', '1 Street', true); "
            "INSERT INTO customer_addresses(address_id, customer_id, label, recipient_name, phone, city, address_line, is_default) "
            "VALUES ('76000000-0000-4000-8000-0000000000b2', "
            f"'{customer}', 'Work', 'Synthetic', '+201000000002', 'Giza', '2 Street', true);",
            "duplicate key",
        )
        # A second customer may have their own default.
        result = self.sql(
            "BEGIN; "
            + fixture
            + "INSERT INTO customer_addresses(address_id, customer_id, label, recipient_name, phone, city, address_line, is_default) "
            "VALUES ('76000000-0000-4000-8000-0000000000b3', "
            f"'{customer}', 'Home', 'Synthetic', '+201000000001', 'Cairo', '1 Street', true); "
            "INSERT INTO customer_addresses(address_id, customer_id, label, recipient_name, phone, city, address_line, is_default) "
            "VALUES ('76000000-0000-4000-8000-0000000000b4', "
            f"'{other}', 'Home', 'Synthetic', '+201000000003', 'Cairo', '3 Street', true); "
            "SELECT 'defaults=' || count(*) FROM customer_addresses WHERE is_default; "
            "ROLLBACK;"
        )
        self.assertIn("defaults=2", result.stdout)
        # A malformed phone is refused.
        self.assert_sql_rejected(
            fixture
            + "INSERT INTO customer_addresses(address_id, customer_id, label, recipient_name, phone, city, address_line) "
            "VALUES ('76000000-0000-4000-8000-0000000000b5', "
            f"'{customer}', 'Home', 'Synthetic', 'call-me', 'Cairo', '1 Street');",
            "check constraint",
        )

    def test_order_price_snapshot_is_independent_from_current_price(self):
        product = "11000000-0000-4000-8000-000000000011"
        customer = "21000000-0000-4000-8000-000000000011"
        order = "71000000-0000-4000-8000-000000000011"
        item = "81000000-0000-4000-8000-000000000011"
        result = self.sql(f"""
            BEGIN;
            INSERT INTO product_registry(product_id, lifecycle) VALUES ('{product}', 'active');
            INSERT INTO product_prices(product_id, amount, currency) VALUES ('{product}', 100, 'EGP');
            INSERT INTO customers(customer_id, email, display_name) VALUES ('{customer}', 'snapshot@example.invalid', 'Snapshot fixture');
            INSERT INTO orders(order_id, customer_id, status, subtotal) VALUES ('{order}', '{customer}', 'confirmed', 200);
            INSERT INTO order_items(order_item_id, order_id, product_id, product_name_snapshot, quantity, unit_price_snapshot, currency)
              VALUES ('{item}', '{order}', '{product}', 'Synthetic snapshot', 2, 100, 'EGP');
            UPDATE product_prices SET amount = 150 WHERE product_id = '{product}';
            SELECT p.amount, i.unit_price_snapshot, i.line_total
              FROM product_prices p JOIN order_items i USING (product_id);
            ROLLBACK;
        """)
        self.assertIn("150.000000|100.000000|200.000000", result.stdout)

    def test_rfm_snapshot_constraints(self):
        customer = "21000000-0000-4000-8000-0000000000ff"
        snapshot = "74000000-0000-4000-8000-0000000000ff"
        customer_row = (
            f"INSERT INTO customers(customer_id, email, display_name) "
            f"VALUES ('{customer}', 'rfm-fixture@example.invalid', 'RFM fixture'); "
        )
        columns = (
            "INSERT INTO rfm_snapshots(snapshot_id, customer_id, reference_date, "
            "observation_start, recency_days, frequency, monetary, recency_score, "
            "frequency_score, monetary_score, segment) "
        )
        for scores, segment, expected in [
            ("6, 3, 3", "'loyal'", "check constraint"),
            ("3, 3, 3", "'unknown'", "check constraint"),
        ]:
            with self.subTest(scores=scores, segment=segment):
                self.assert_sql_rejected(
                    customer_row
                    + columns
                    + f"VALUES ('{snapshot}', '{customer}', CURRENT_DATE, "
                    f"CURRENT_DATE - 365, 1, 1, 100, {scores}, {segment});",
                    expected,
                )
        self.assert_sql_rejected(
            customer_row
            + columns
            + f"VALUES ('{snapshot}', '{customer}', CURRENT_DATE, "
            f"CURRENT_DATE + 1, 1, 1, 100, 3, 3, 3, 'loyal');",
            "check constraint",
        )
        duplicate = self.sql(
            f"BEGIN; {customer_row}"
            + columns
            + f"VALUES ('{snapshot}', '{customer}', CURRENT_DATE, "
            f"CURRENT_DATE - 365, 1, 1, 100, 3, 3, 3, 'loyal');"
            + columns.replace(str(snapshot), "74000000-0000-4000-8000-0000000000fe")
            + f"VALUES ('74000000-0000-4000-8000-0000000000fe', '{customer}', "
            f"CURRENT_DATE, CURRENT_DATE - 365, 1, 1, 100, 3, 3, 3, 'loyal'); "
            "ROLLBACK;",
            check=False,
        )
        self.assertNotEqual(duplicate.returncode, 0, duplicate.stdout)
        self.assertIn("duplicate key", duplicate.stderr)

    def test_synthetic_seeds_apply_to_isolated_databases(self):
        seed_database = "seed_test"
        run("docker", "exec", self.postgres, "createdb", "-h", "127.0.0.1", "-U", "postgres", seed_database)
        try:
            # Every migration and every seed, so a new seed file is covered here
            # without having to remember to add it.
            for path in [
                *sorted((ROOT / "database/relational/migrations").glob("*.sql")),
                *sorted((ROOT / "database/relational/seeds").glob("*.sql")),
            ]:
                result = run(
                    "docker", "exec", "-i", self.postgres, "psql", "-h", "127.0.0.1",
                    "-U", "postgres", "-d", seed_database, "-X", "-v", "ON_ERROR_STOP=1",
                    stdin=path.read_text(),
                )
                self.assertEqual(result.returncode, 0)
            count = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT count(*) FROM product_registry WHERE lifecycle='active';",
            )
            self.assertEqual(count.stdout.strip(), "13")
            demand_count = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT count(*) FROM inventory_movements WHERE reference_type='synthetic_demand_history';",
            )
            self.assertEqual(demand_count.stdout.strip(), str(13 * 210))
            pricing_count = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT count(*) FROM pricing_observations;",
            )
            self.assertEqual(pricing_count.stdout.strip(), "13")
            stale_count = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT count(*) FROM pricing_observations "
                "WHERE observed_at < CURRENT_TIMESTAMP - interval '24 hours';",
            )
            self.assertEqual(stale_count.stdout.strip(), "1")
            applied_count = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT count(*) FROM price_changes;",
            )
            self.assertEqual(applied_count.stdout.strip(), "0")
            rfm_counts = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT (SELECT count(*) FROM customers), "
                "(SELECT count(*) FROM orders), "
                "(SELECT count(*) FROM orders WHERE refund_total > 0), "
                "(SELECT count(*) FROM orders WHERE created_at::date < CURRENT_DATE - 364), "
                "(SELECT count(*) FROM orders WHERE created_at::date >= CURRENT_DATE - 364 "
                " AND status IN ('confirmed','shipped','delivered','refunded') "
                " AND subtotal - refund_total > 0), "
                "(SELECT count(DISTINCT customer_id) FROM orders "
                " WHERE created_at::date >= CURRENT_DATE - 364 "
                " AND status IN ('confirmed','shipped','delivered','refunded') "
                " AND subtotal - refund_total > 0);",
            )
            self.assertEqual(rfm_counts.stdout.strip(), "40|518|70|42|342|38")
            analytics_counts = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT (SELECT count(*) FROM browsing_events), "
                "(SELECT count(DISTINCT session_id) FROM browsing_events), "
                "(SELECT count(*) FROM browsing_events WHERE customer_id IS NULL), "
                "(SELECT count(*) FROM order_items), "
                "(SELECT count(*) FROM ("
                "  SELECT o.order_id FROM orders o JOIN order_items i USING (order_id) "
                "  GROUP BY o.order_id, o.subtotal HAVING sum(i.line_total) <> o.subtotal"
                ") mismatched);",
            )
            self.assertEqual(analytics_counts.stdout.strip(), "9000|2251|2700|1021|0")
            index_count = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT count(*) FROM pg_indexes WHERE indexname IN "
                "('browsing_events_occurred_idx', 'order_items_product_idx');",
            )
            self.assertEqual(index_count.stdout.strip(), "2")
            # Shipment fixtures: every fulfilled order gets one shipment with a
            # timeline; cancelled and failed-payment orders get none, and no
            # shipment is left without events.
            shipment_counts = run(
                "docker", "exec", self.postgres, "psql", "-h", "127.0.0.1", "-U", "postgres",
                "-d", seed_database, "-X", "-A", "-t", "-c",
                "SELECT (SELECT count(*) FROM shipments) > 0, "
                "(SELECT count(*) FROM shipments s JOIN orders o USING (order_id) "
                " WHERE o.status IN ('cancelled', 'payment_failed')), "
                "(SELECT count(*) FROM orders o "
                " WHERE o.status IN ('confirmed', 'shipped', 'delivered', 'refunded') "
                "   AND o.completed_at IS NOT NULL "
                "   AND NOT EXISTS (SELECT 1 FROM shipments s WHERE s.order_id = o.order_id)), "
                "(SELECT count(*) FROM shipments s "
                " WHERE NOT EXISTS (SELECT 1 FROM shipment_events e "
                "                    WHERE e.shipment_id = s.shipment_id)), "
                "(SELECT count(*) FROM shipment_events) > 0;",
            )
            self.assertEqual(shipment_counts.stdout.strip(), "t|0|0|0|t")
        finally:
            run("docker", "exec", self.postgres, "dropdb", "-h", "127.0.0.1", "-U", "postgres", "--force", seed_database, check=False)

        run("docker", "exec", self.mongo, "mongosh", "--quiet",
            f"mongodb://127.0.0.1:27017/{seed_database}", "--file", "database/catalog/setup.js")
        run("docker", "exec", self.mongo, "mongosh", "--quiet",
            f"mongodb://127.0.0.1:27017/{seed_database}", "--file", "database/catalog/seed.synthetic.js")
        result = self.js_in_database(seed_database, "checks.equal(await db.products.countDocuments(), 13); print('thirteen catalog seeds');")
        self.assertIn("thirteen catalog seeds", result.stdout)
        self.js_in_database(seed_database, "await db.dropDatabase();")

    def test_mongo_identity_validation_and_authority_boundaries(self):
        # Every fixture is synthetic and removed only from this task-owned database.
        self.js(f"""
            const base = {{
                _id: '{PRODUCT_ID}', name: 'Synthetic fixture', description: '',
                categories: ['fixture'], attributes: {{color: 'neutral'}},
                images: [{{uri: 'https://example.invalid/item.png', alt: 'Fixture'}}],
                provenance: {{kind: 'synthetic', dataset_id: 'schema-tests-v1'}},
                created_at: new Date(), updated_at: new Date()
            }};
            await db.products.insertOne(base);
            checks.equal((await db.products.findOne({{_id: base._id}}))._id, base._id);
            let duplicateCode;
            try {{ await db.products.insertOne(base); }}
            catch (error) {{ duplicateCode = error.code; }}
            checks.equal(duplicateCode, 11000);
            for (const patch of [
                {{price: '9.99'}}, {{stock: 10}}, {{lifecycle: 'active'}},
                {{_id: 'different-id'}}, {{provenance: {{kind: 'unknown', dataset_id: 'x'}}}},
                {{created_at: 'not-a-date'}}, {{name: '   '}}, {{categories: ['duplicate', 'duplicate']}},
                {{images: [{{uri: 'javascript:alert(1)', alt: ''}}]}}, {{attributes: {{count: 3}}}}
            ]) {{
                // _id mutation is rejected by either immutable identity or schema validation.
                let rejectionCode;
                try {{ await db.products.replaceOne({{_id: base._id}}, {{...base, ...patch}}); }}
                catch (error) {{ rejectionCode = error.code; }}
                checks([66, 121].includes(rejectionCode), 'Expected rejection for ' + JSON.stringify(patch));
            }}
            checks.equal(await db.products.countDocuments({{_id: base._id}}), 1);
        """)

    def test_mongo_setup_is_repeatable_and_keeps_records(self):
        # This ID differs from the validation test so tests are order-independent.
        other = "20000000-0000-4000-8000-000000000002"
        self.js(f"""
            await db.products.insertOne({{
                _id: '{other}', name: 'Persistence fixture', description: '',
                categories: [], attributes: {{}}, images: [],
                provenance: {{kind: 'synthetic', dataset_id: 'schema-tests-v1'}},
                created_at: new Date(), updated_at: new Date()
            }});
        """)
        self.setup_catalog()
        result = self.js(f"""
            checks.equal(await db.products.countDocuments({{_id: '{other}'}}), 1);
            checks((await db.products.getIndexes()).some(i => i.name === 'category_product_id'));
            print('catalog setup preserved records');
        """)
        self.assertIn("catalog setup preserved records", result.stdout)
