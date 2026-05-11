"""
WebSocket hub. Manages subscriptions and fan-out to connected clients.

Protocol (from docs/API_CONTRACTS.md §websocket):
  Client → server: { op: subscribe|unsubscribe|ping, channels: [...] }
  Server → client: { type, channel, data } or { type: pong }

Channels:
  price.NG.front        — synthetic tick stream
  price.NG.front.1m     — 1-minute bar stream
  signal.NG             — signal update
  events.NG             — news event push
  alerts                — alert push
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# channel → set of websockets subscribed to it
_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)


async def connect(ws: WebSocket) -> None:
    await ws.accept()
    logger.debug("WebSocket connected: %s", id(ws))


def subscribe(ws: WebSocket, channels: list[str]) -> None:
    for ch in channels:
        _subscriptions[ch].add(ws)
    logger.debug("WebSocket %s subscribed to %s", id(ws), channels)


def unsubscribe(ws: WebSocket, channels: list[str]) -> None:
    for ch in channels:
        _subscriptions[ch].discard(ws)


def disconnect(ws: WebSocket) -> None:
    for subs in _subscriptions.values():
        subs.discard(ws)
    logger.debug("WebSocket disconnected: %s", id(ws))


async def broadcast(channel: str, msg_type: str, data: dict) -> None:  # type: ignore[type-arg]
    """Send a message to all subscribers of channel. Dead connections are pruned."""
    dead: list[WebSocket] = []
    payload = json.dumps({"type": msg_type, "channel": channel, "data": data})
    for ws in list(_subscriptions.get(channel, set())):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        disconnect(ws)


async def handle_connection(ws: WebSocket) -> None:
    """Main read loop for a single WebSocket connection."""
    await connect(ws)
    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=35.0)
            except asyncio.TimeoutError:
                # Heartbeat pong
                await ws.send_text(json.dumps({"type": "pong"}))
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            op = msg.get("op")
            channels = msg.get("channels", [])

            if op == "subscribe":
                subscribe(ws, channels)
            elif op == "unsubscribe":
                unsubscribe(ws, channels)
            elif op == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except Exception:
        pass
    finally:
        disconnect(ws)
