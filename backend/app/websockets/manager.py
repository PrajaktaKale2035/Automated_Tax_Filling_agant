"""WebSocket connection manager.

Phase 3: tracks per-client connections so backend can route filing progress
events (filing.computing, filing.complete, ...) to a specific user's channel.
Falls back to broadcast() for general announcements.
"""
from typing import Dict, List, Optional

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # client_id -> list of active WebSocket connections (a user may have
        # multiple tabs open).
        self._by_client: Dict[str, List[WebSocket]] = {}
        # Legacy flat list, used only by the global broadcast() path.
        self._all: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> None:
        await websocket.accept()
        self._all.append(websocket)
        if client_id:
            self._by_client.setdefault(client_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: Optional[str] = None) -> None:
        if websocket in self._all:
            self._all.remove(websocket)
        if client_id and client_id in self._by_client:
            try:
                self._by_client[client_id].remove(websocket)
            except ValueError:
                pass
            if not self._by_client[client_id]:
                self._by_client.pop(client_id, None)

    async def broadcast(self, message: dict) -> None:
        """Send to every connected client. Best-effort - failures are swallowed."""
        for ws in list(self._all):
            try:
                await ws.send_json(message)
            except Exception:
                # The peer may have gone away; skip.
                continue

    async def send_to_client(self, client_id: str, message: dict) -> int:
        """Send to a specific client_id's connections. Returns # of sends.

        Returns 0 if no connection is registered for client_id.
        """
        sent = 0
        for ws in list(self._by_client.get(client_id, [])):
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                continue
        return sent


manager = ConnectionManager()
