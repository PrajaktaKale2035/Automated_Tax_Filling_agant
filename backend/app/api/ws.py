"""WebSocket router.

Phase 0: AutoGen retired. This is an echo stub.
Phase 3 will wire LangGraph state events (filing.researching, filing.calculating,
filing.complete) into this channel.
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets.manager import manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    await websocket.send_json({
        "sender": "system",
        "event": "connected",
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

            # Phase 0: echo back. Phase 3 will route to LangGraph events.
            await websocket.send_json({
                "sender": "assistant",
                "event": "echo",
                "message": f"Phase 0 stub: received '{user_message}'",
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
