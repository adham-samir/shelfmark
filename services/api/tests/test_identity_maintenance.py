"""Session maintenance: the reaper only removes rows that cannot authenticate."""

from contextlib import contextmanager

from smart_ecommerce_api import db
from smart_ecommerce_api.identity import SessionReaper


class _RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.deleted = 3

    def execute(self, query: str, _params: object = None):
        self.statements.append(" ".join(query.split()))
        connection = self

        class _Cursor:
            def fetchall(self):
                return [{"session_id": index} for index in range(connection.deleted)]

        return _Cursor()


def test_reaper_deletes_only_unusable_sessions(monkeypatch) -> None:
    connection = _RecordingConnection()

    @contextmanager
    def fake_connection(_dsn, row_factory=None):
        yield connection

    monkeypatch.setattr(db, "connection", fake_connection)

    assert SessionReaper("postgresql://unused").run() == 3
    assert len(connection.statements) == 1
    statement = connection.statements[0]
    assert statement.startswith("DELETE FROM sessions")
    # Expired rows always go; revoked rows only after the retention window.
    assert "expires_at <= CURRENT_TIMESTAMP" in statement
    assert "revoked_at IS NOT NULL" in statement
    assert "interval '30 days'" in statement
