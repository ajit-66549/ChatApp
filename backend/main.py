from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from connection_manager import manager
from schemas import IncomingMessage
from pydantic import ValidationError
from dotenv import load_dotenv
from database import engine, Base
from contextlib import asynccontextmanager
import os
import json

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            print("Database connected successfully")
    except Exception:
        print("DB connection failed")
        raise
        
    yield
    
    await engine.dispose()
    print("Database connection closed")

app = FastAPI(title=os.getenv("APP_NAME", "ChatApp"), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "ChatApp backend is running."}

@app.get("/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    return {"status": "ok", "database": db_status}

@app.get("/clients")
def clients():
    return {
        "count": manager.count(),
        "client_id": manager.get_client_ids()
    }
    
@app.get("/rooms")
def rooms():
    return {
        pin: {
            "members": list(members),
            "count": len(members)
        }
        for pin, members in manager.rooms.items()
    }
    
@app.websocket("/ws/{client_id}")
async def websocket_endpoints(websocket: WebSocket, client_id: str):
    connected = await manager.connect(client_id, websocket)
    if not connected:
        return
    
    await manager.send_to(client_id, {
        "type": "system",
        "text": "You are in the lobby"
    })
    
    await manager.broadcast({
        "type": "system",
        "text": f"{client_id} joined the chat",
        "online_count": manager.count()
    }, exclude=client_id)
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                event = IncomingMessage.model_validate(json.loads(raw_data))
            except (ValidationError, json.JSONDecodeError):
                await manager.send_to(client_id, {
                    "type": "error",
                    "text": "Invalid message format"
                })
                continue
            
            if event.type == "ping":
                await manager.send_to(client_id, {"type": "pong"})
                
            elif event.type == "create_room":
                room_pin = manager.create_room()
                manager.join_room(client_id, room_pin)
                
                await manager.send_to(client_id, {
                    "type": "room_created",
                    "text": "Room created! Share this PIN with others.",
                    "room_pin": room_pin,
                    "online_count": manager.get_room_count(room_pin)
                })
                
            elif event.type =="join_room":
                if not event.pin:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "error": "PIN is required to join room"
                    })
                    continue
                
                success = manager.join_room(client_id, event.pin)
                if not success:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "text": f"{event.pin} is an invalid PIN"
                    })
                    continue
                
                await manager.send_to(client_id, {
                    "type": "room_joined",
                    "text": f"Joined room {event.pin}",
                    "room_pin": event.pin,
                    "online_count": manager.get_room_count(event.pin)
                })
                
                await manager.broadcast_to_room(event.pin, {
                    "type": "system",
                    "text": f"{client_id} joined the room",
                    "room_pin": event.pin,
                    "room_count": manager.get_room_count(event.pin)
                    }, exclude=client_id)
            
            elif event.type == "leave_room":
                pin = manager.get_client_room(client_id)
                
                if not pin:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "text": "You are not in any room"
                    })
                    continue
                
                await manager.broadcast_to_room(pin, {
                    "type": "system",
                    "text": f"{client_id} left the room",
                    "room_count": manager.get_room_count(pin) - 1
                    }, exclude=client_id)
                
                manager.leave_room(client_id)
                
                await manager.send_to(client_id, {
                    "type": "room_left",
                    "text": "You left the room. Back in lobby"
                })
                
            elif event.type == "message":
                pin = manager.get_client_room(client_id)
                
                if pin:
                    await manager.broadcast_to_room(pin, {
                        "type": "message",
                        "client_id": client_id,
                        "text": event.text,
                        "online_count": manager.get_room_count(pin)
                        })
                    
                else:
                    await manager.broadcast({
                        "type": "message",
                        "client_id": client_id,
                        "text": event.text,
                        "online_count": manager.count()
                    })
    
    except WebSocketDisconnect:
        pin = manager.get_client_room(client_id)
        
        if pin:
            await manager.broadcast_to_room(pin, {
            "type": "system",
            "room_pin": pin,
            "text": f"{client_id} disconnected",
            "room_count": manager.get_room_count(pin) - 1
        }, exclude=client_id)
        else:
            await manager.broadcast({
                "type": "system",
                "text": f"{client_id} disconnected"
            }, exclude=client_id)
        
        manager.disconnect(client_id)