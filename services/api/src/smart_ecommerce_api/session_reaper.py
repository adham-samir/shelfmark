"""One-shot session cleanup entry point for a daily scheduler.

Expired and revoked session rows are ignored on read but never deleted, so the
table would grow without bound on a long-running deployment. This job removes
rows that can no longer authenticate anyone.
"""

import json

from . import db
from .config import Settings
from .identity import SessionReaper

def main() -> None:
    try:
        _run()
    finally:
        db.close_pools()


def _run() -> None:
    settings = Settings.from_environment()
    removed = SessionReaper(settings.postgres_dsn).run()
    print(json.dumps({"sessions_removed": removed}, indent=2))

if __name__ == "__main__":
    main()
