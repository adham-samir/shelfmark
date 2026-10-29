"""One-shot BO-03 RFM segmentation entry point for a daily scheduler."""

import json

from . import db
from .config import Settings
from .segmentation import SegmentationService, SegmentationStore


def main() -> None:
    try:
        _run()
    finally:
        db.close_pools()


def _run() -> None:
    settings = Settings.from_environment()
    service = SegmentationService(SegmentationStore(settings.postgres_dsn))
    print(
        json.dumps(service.run().model_dump(mode="json"), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()