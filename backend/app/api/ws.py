"""WebSocket router for filing progress + completion events.

Phase 3: clients connect with `/api/ws/{client_id}`. The backend pushes
filing.* events keyed to that client_id when filings are computed.

Message protocol (server → client):
  { "type": "message",     "content": "..." }      — chat / status text
  { "type": "rag_sources", "sources": [...] }       — RAG retrieval metadata
  { "type": "error",       "detail": "..." }        — error detail
  { "event": "...", ... }                           — legacy filing.* events
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets.manager import manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    # Announce connection using the typed protocol so the frontend handler
    # can parse it the same way as every other server → client message.
    await websocket.send_json({
        "type": "message",
        "content": "Connected to Indian Tax Filing Assistant",
        # Also keep the legacy fields so old clients aren't broken.
        "event": "connected",
        "client_id": client_id,
    })
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                user_message = payload.get("message", raw)
            except json.JSONDecodeError:
                user_message = raw

            # Echo inbound messages back so the frontend can confirm delivery.
            # Real filing progress is pushed server-side via manager.send_to_client().
            await websocket.send_json({
                "type": "message",
                "content": user_message,
                # Legacy compat
                "event": "echo",
                "message": user_message,
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
