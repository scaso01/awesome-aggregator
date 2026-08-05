"""WebSocket connection manager for real-time content updates."""

import json
from typing import Any

from fastapi import WebSocket

from backend.config import logger


class ConnectionManager:
    """Manages WebSocket connections and broadcasts updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]):
        """Send a message to all connected clients."""
        if not self.active_connections:
            return

        text = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(text)
            except Exception:
                disconnected.append(connection)

        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)

    async def send_new_content(self, source_id: int, items: list[dict]):
        """Broadcast new content items to all clients."""
        await self.broadcast({
            "type": "new_content",
            "source_id": source_id,
            "items": items,
        })

    async def send_source_update(self, source_id: int, status: str,
                                  error: str = None):
        """Broadcast a source status update."""
        await self.broadcast({
            "type": "source_update",
            "source_id": source_id,
            "status": status,
            "error": error,
        })

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Singleton instance
manager = ConnectionManager()
