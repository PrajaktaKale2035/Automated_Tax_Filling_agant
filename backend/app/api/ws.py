"""WebSocket router for filing progress + completion events.

Phase 3: clients connect with `/api/ws/{client_id}`. The backend pushes
filing.* events keyed to that client_id when filings are computed.
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets.manager import manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    await websocket.send_json({
        "event": "connected",
        "client_id": client_id,
        "message": "Connected to Indian Tax Filing Assistant",
    })
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", data)
            except json.JSONDecodeError:
                user_message = data

            # Phase 3 leaves the inbound channel as a passthrough echo for
            # heartbeats / debugging. Real filing progress is pushed by
            # backend handlers via manager.send_to_client().
            await websocket.send_json({
                "event": "echo",
                "message": user_message,
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
