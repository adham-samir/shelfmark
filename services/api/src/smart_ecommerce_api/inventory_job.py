"""One-shot BO-01 job entry point for a daily scheduler."""

import json

from . import db
from .config import Settings
from .forecasting import InventoryService, InventoryStore, SandboxSupplierSimulator


def main() -> None:
    try:
        _run()
    finally:
        db.close_pools()


def _run() -> None:
    settings = Settings.from_environment()
    service = InventoryService(
        InventoryStore(settings.postgres_dsn),
        settings.forecast_artifact,
        SandboxSupplierSimulator(),
    )
    print(json.dumps(service.run().model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
