"""WebSocket completion-event tests (Phase 3)."""
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import User


client = TestClient(app)


def _override_db(session):
    def _gen():
        yield session
    app.dependency_overrides[get_db] = _gen


def test_ws_connect_emits_connected_event():
    with client.websocket_connect("/api/ws/test-client-1") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "connected"
        assert msg["client_id"] == "test-client-1"


def test_ws_echo_for_inbound_messages():
    with client.websocket_connect("/api/ws/test-client-2") as ws:
        ws.receive_json()  # drain "connected"
        ws.send_text("ping")
        msg = ws.receive_json()
        assert msg["event"] == "echo"
        assert msg["message"] == "ping"


def test_filing_start_emits_filing_complete_to_client(db_session):
    """When client_id is supplied, filing progress events are routed to it."""
    user = User(id=77, email="ws@test.in", hashed_password="x", full_name="WS User")
    db_session.add(user); db_session.commit()
    _override_db(db_session)

    try:
        with client.websocket_connect("/api/ws/ws-77") as ws:
            ws.receive_json()  # drain "connected"

            resp = client.post("/api/v2/filing/start", json={
                "user_id": 77,
                "regime": "new",
                "salary": {"gross": 600_000, "tds": 0},
                "deductions": {},
                "client_id": "ws-77",
            })
            assert resp.status_code == 200, resp.text

            # Collect emitted events; expect filing.starting, filing.calculating, filing.complete.
            events = []
            for _ in range(3):
                events.append(ws.receive_json())

            event_names = [e["event"] for e in events]
            assert "filing.starting" in event_names
            assert "filing.calculating" in event_names
            assert "filing.complete" in event_names

            complete = next(e for e in events if e["event"] == "filing.complete")
            assert complete["regime"] == "new"
            assert complete["total_tax"] == 0
            assert complete["filing_id"] == resp.json()["filing_id"]
            assert complete["pdf_url"].endswith("/pdf")
            assert complete["json_url"].endswith("/json")
    finally:
        app.dependency_overrides.clear()
