"""One-shot BO-02 pricing entry point for a daily scheduler."""

import json

from . import db
from .config import Settings
from .pricing import PricingService, PricingStore, SeasonCalendar


def main() -> None:
    try:
        _run()
    finally:
        db.close_pools()


def _run() -> None:
    settings = Settings.from_environment()
    service = PricingService(
        PricingStore(settings.postgres_dsn),
        SeasonCalendar(settings.pricing_seasons),
    )
    print(
        json.dumps(service.run().model_dump(mode="json"), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()