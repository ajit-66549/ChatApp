from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import ValidationError
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from connection_manager import manager
from schemas import IncomingMessage, MessageResponse, PaginatedMessage
from database import engine, Base
from database import engine, get_db
from crud import (
    save_message,
    get_user_by_username,
    create_user,
    get_room_by_pin,
    create_room as db_create_room,
    delete_room,
    get_lobby_messages,
    get_room_messages,
    cout_room_messages,
    count_lobby_messages,
    explain_lobby_message,
    explain_room_message
)

from dotenv import load_dotenv
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
            await conn.execute(text("SELECT 1"))
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
    
@app.get("/history/lobby", response_model=PaginatedMessage)
async def lobby_history(limit: int = Query(default=50, ge=1, le=100),
                        offset: int = Query(default=0, ge=0),
                        db: AsyncSession = Depends(get_db)):
    messages = await get_lobby_messages(db, limit=limit, offset=offset)
    total = await count_lobby_messages(db)
    
    return PaginatedMessage(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset+limit) < total
    )
    
@app.get("history/room/{pin}", response_model=PaginatedMessage)
async def room_mesages(pin: str,
                       limit: int = Query(default=50, ge=1, le=100),
                       offset: int = Query(default=0, ge=0),
                       db: AsyncSession = Depends(get_db)):
    room = await get_room_by_pin(db, pin)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {pin} not found")
    
    messages = await get_room_messages(db, room_id=room.id, limit=limit, offset=offset)
    total = await cout_room_messages(db, room_id=room.id)
    
    return PaginatedMessage(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(limit+offset) < total
    )
    
@app.websocket("/ws/{client_id}")
async def websocket_endpoints(websocket: WebSocket, client_id: str, db: AsyncSession = Depends(get_db)):
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
                
                await db_create_room(db, room_pin)
                
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
                sender = await get_user_by_username(db, client_id)
                if not sender:
                    sender = await create_user(
                        db,
                        username=client_id,
                        hashed_password="ws_guest_user"
                    )
                
                if pin:
                    room = await get_room_by_pin(db, pin)
                    if room:
                        await save_message(
                            db, text=event.text, user_id=sender.id, room_id=room.id
                        )
                        
                    await manager.broadcast_to_room(pin, {
                        "type": "message",
                        "client_id": client_id,
                        "text": event.text,
                        "online_count": manager.get_room_count(pin)
                        })
                    
                else:
                    await save_message(
                        db, text=event.text, user_id=sender.id, room_id=None
                    )
                    
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
        
@app.get("/debug/explain/lobby")
async def explain_lobby(db: AsyncSession = Depends(get_db)):
    plan = await explain_lobby_message(db)
    return {"Query plan": plan}

@app.get("/debug/explain/room/{pin}")
async def explain_room(pin: str, db: AsyncSession = Depends(get_db)):
    room = await get_room_by_pin(db, pin=pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    plan = await explain_lobby_message(db, room.id)
    return {"Query_plan": plan}