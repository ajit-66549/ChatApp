from fastapi import WebSocket
from typing import Dict
import json


class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> bool:
        await websocket.accept()

        old_socket = self.connections.get(client_id)
        if old_socket:
            await old_socket.close(code=1000)

        self.connections[client_id] = websocket
        return True

    def disconnect(self, client_id: str):
        self.connections.pop(client_id, None)

    def count(self) -> int:
        return len(self.connections)

    def get_client_ids(self) -> list:
        return list(self.connections.keys())

    async def send_to(self, client_id: str, payload: dict):
        ws = self.connections.get(client_id)
        if ws:
            await ws.send_text(json.dumps(payload))

    async def broadcast(self, payload: dict, exclude: str = None):
        for client_id, ws in self.connections.items():
            if exclude and client_id == exclude:
                continue
            await ws.send_text(json.dumps(payload))


manager = ConnectionManager()