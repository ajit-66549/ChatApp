from fastapi import WebSocket
from typing import Dict, Set, Optional
import json
import random

def generate_pin():
        return str(random.randint(100000, 999999))      # generates random 6-digit pin and convert into string 

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}  
        self.rooms: Dict[str, Set[str]] = {}
        self.client_room: Dict[str, Optional[str]] = {}
        
    # connection
    async def connect(self, client_id: str, websocket: WebSocket) -> bool:
        await websocket.accept()

        old_socket = self.connections.get(client_id)
        if old_socket:
            await old_socket.close(code=1000)

        self.connections[client_id] = websocket
        self.client_room[client_id] = None    
        return True
    
    def count(self) -> int:
        return len(self.connections)

    def get_client_ids(self) -> list:
        return list(self.connections.keys())

    async def send_to(self, client_id: str, payload: dict):
        ws = self.connections.get(client_id)
        if ws:
            await ws.send_text(json.dumps(payload))
            
    # send message to all clients who are not in any room
    async def broadcast(self, payload: dict, exclude: str = None):
        for client_id, ws in self.connections.items():
            if exclude and client_id == exclude:
                continue
            if self.client_room.get(client_id) is None:
                await ws.send_text(json.dumps(payload))
            
    def disconnect(self, client_id: str):
        self.leave_room(client_id)
        self.client_room.pop(client_id, None)
        self.connections.pop(client_id, None)
    
    # room
    def create_room(self) -> str:
        pin = generate_pin()
        
        while pin in self.rooms:
            pin = generate_pin()    # generate unique pin
            
        self.rooms[pin] = set()
        return pin
    
    def join_room(self, client_id: str, pin: str) -> bool:
        if pin not in self.rooms:
            return False
        
        # leave the current room to join another
        current_pin = self.client_room.get(client_id)
        if current_pin and current_pin in self.rooms:
            self.rooms[current_pin].discard(client_id)
            
        self.rooms[pin].add(client_id)
        self.client_room[client_id] = pin
        return True
    
    def get_client_room(self, client_id: str) -> Optional[str]:
        return self.client_room.get(client_id)
    
    def get_room_members(self, pin: str) -> Set[str]:
        return self.rooms.get(pin, set())    
    
    def get_room_count(self, pin: str) -> int:
        return len(self.get_room_members(pin)) 
    
    async def broadcast_to_room(self, pin: str, payload: dict, exclude: str = None):
        for client_id in self.get_room_members(pin):
            if exclude and client_id == exclude:
                continue
            await self.send_to(client_id, payload)
    
    def leave_room(self, client_id: str):
        pin = self.client_room.get(client_id)
        if pin and pin in self.rooms:
            self.rooms[pin].discard(client_id)
            
            # delete room if everybody leaves
            if len(self.rooms[pin]) == 0:
                del self.rooms[pin]
            
        self.client_room[client_id] = None
         
manager = ConnectionManager()