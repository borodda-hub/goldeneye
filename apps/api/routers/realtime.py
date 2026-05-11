from fastapi import APIRouter, WebSocket

from apps.api.realtime.gateway import handle_connection

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await handle_connection(ws)
