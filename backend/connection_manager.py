from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        self.activate_connections: List[WebSocket]= []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.activate_connections.append(websocket)
        print(f"Total Connected Clients: {len(self.activate_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        self.activate_connections.remove(websocket)
        print("Client Removed")
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    async def broadcast(self, message: str):
        for connection in self.activate_connections:
            await connection.send_text(message)
            