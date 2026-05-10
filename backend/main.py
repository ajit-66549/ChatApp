from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from pydantic import ValidationError


from repositories import UserRepository, RoomRepository, MessageRepository
from schemas import IncomingMessage, PaginatedMessages, MessageResponse
from authentication.websocket_auth import authenticate_websocket_user
from authentication.dependencies import get_current_user
from connection_manager import manager
from authentication import auth_router
from database import engine, get_db
from models import User

import os
import json
from dotenv import load_dotenv

import time
import logging
from latency import log_message_latency
from messaging.messagequeue import MessageQueue
from messaging.queuedmessage import QueuedMessage

load_dotenv()

message_queue = MessageQueue()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        print("✅ Database connected successfully")
    await message_queue.ping()
    print("✅ Redis connected successfully")
    yield
    await message_queue.close()
    await engine.dispose()
    print("Database connection closed")


app = FastAPI(title=os.getenv("APP_NAME", "ChatApp"), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    try:
        await message_queue.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {str(e)}"
        
    return {"status": "ok", "database": db_status, "redis": redis_status}

@app.get("/redis/ping")
async def redis_ping():
    try:
        await message_queue.ping()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis ping failed: {str(e)}")
    return {"ping": "pong"}

@app.get("/clients")
def clients():
    return {
        "count": manager.count(),
        "clients": manager.get_client_ids()
    }


@app.get("/rooms")
def rooms():
    return {
        pin: {"members": list(members), "count": len(members)}
        for pin, members in manager.rooms.items()
    }


@app.get("/debug/explain/lobby")
async def explain_lobby(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = MessageRepository(db)
    plan = await repo.explain_lobby()
    return {"query_plan": plan}


@app.get("/debug/explain/room/{pin}")
async def explain_room(
    pin: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room_repo = RoomRepository(db)
    room = await room_repo.get_by_pin(pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    msg_repo = MessageRepository(db)
    plan = await msg_repo.explain_room(room.id)
    return {"query_plan": plan}


@app.get("/history/lobby", response_model=PaginatedMessages)
async def lobby_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = MessageRepository(db)
    messages = await repo.get_lobby_messages(limit=limit, offset=offset)
    total = await repo.count_lobby_messages()
    return PaginatedMessages(
        messages=[
            MessageResponse(
                id=m.id,
                text=m.text,
                user_id=m.user_id,
                username=m.user.username,
                room_id=m.room_id,
                created_at=m.created_at
            )
            for m in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total
    )


@app.get("/history/room/{pin}", response_model=PaginatedMessages)
async def room_history(
    pin: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room_repo = RoomRepository(db)
    room = await room_repo.get_by_pin(pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    msg_repo = MessageRepository(db)
    messages = await msg_repo.get_room_messages(room_id=room.id, limit=limit, offset=offset)
    total = await msg_repo.count_room_messages(room_id=room.id)
    return PaginatedMessages(
        messages=[
            MessageResponse(
                id=m.id,
                text=m.text,
                user_id=m.user_id,
                username=m.user.username,
                room_id=m.room_id,
                created_at=m.created_at
            )
            for m in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total
    )


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_websocket_user(token=token, db=db)
    if not user:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    client_id = user.username

    connected = await manager.connect(client_id, websocket)
    if not connected:
        return

    await manager.send_to(client_id, {
        "type": "system",
        "text": f"Welcome {client_id}! You are in the lobby."
    })

    await manager.broadcast({
        "type": "system",
        "text": f"{client_id} joined the lobby",
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
                    "error": "Invalid message format"
                })
                continue

            if event.type == "ping":
                await manager.send_to(client_id, {"type": "pong"})

            elif event.type == "create_room":
                room_pin = manager.create_room()
                manager.join_room(client_id, room_pin)
                room_repo = RoomRepository(db)
                await room_repo.create(room_pin)
                await manager.send_to(client_id, {
                    "type": "room_created",
                    "text": "Room created! Share this PIN with others.",
                    "room_pin": room_pin,
                    "online_count": manager.get_room_count(room_pin)
                })

            elif event.type == "join_room":
                if not event.pin:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "error": "PIN is required to join room"
                    })
                    continue

                room_repo = RoomRepository(db)
                room = await room_repo.get_by_pin(event.pin)
                if not room:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "error": f"Invalid PIN: {event.pin}"
                    })
                    continue

                success = manager.join_room(client_id, event.pin)
                if not success:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "error": f"Could not join room: {event.pin}"
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
                    "online_count": manager.get_room_count(event.pin)
                }, exclude=client_id)

            elif event.type == "leave_room":
                pin = manager.get_client_room(client_id)
                if not pin:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "error": "You are not in any room"
                    })
                    continue

                await manager.broadcast_to_room(pin, {
                    "type": "system",
                    "text": f"{client_id} left the room",
                    "online_count": manager.get_room_count(pin) - 1
                }, exclude=client_id)

                manager.leave_room(client_id)

                await manager.send_to(client_id, {
                    "type": "room_left",
                    "text": "You left the room. Back in lobby."
                })

            elif event.type == "message":
                receive_at = time.perf_counter()
                
                if not event.text:
                    await manager.send_to(client_id, {
                        "type": "error",
                        "error": "Message text cannot be empty"
                    })
                    continue
                
                pin = manager.get_client_room(client_id)
                msg_repo = MessageRepository(db)
                room_id = None

                if pin:
                    room_repo = RoomRepository(db)
                    room = await room_repo.get_by_pin(pin)

                    if not room:
                        await manager.send_to(client_id, {
                            "type": "error",
                            "error": "Room no longer exists"
                        })
                        manager.leave_room(client_id)
                        continue

                    if client_id not in manager.get_room_members(pin):
                        await manager.send_to(client_id, {
                            "type": "error",
                            "error": "You are not a member of this room"
                        })
                        continue

                    _, db_stage_timings = await msg_repo.save_message_with_timings(
                        text=event.text,
                        user_id=user.id,
                        room_id=room.id
                    )
                    db_save_at = time.perf_counter()

                    room_id = room.id
                    await manager.broadcast_to_room(pin, {
                        "type": "message",
                        "client_id": client_id,
                        "text": event.text,
                        "room_pin": pin,
                        "online_count": manager.get_room_count(pin)
                    })
                    broadcast_at = time.perf_counter()
                    
                    log_message_latency(client_id, f"room:{pin}", receive_at, db_save_at, broadcast_at, db_stage_timings=db_stage_timings)
                else:
                    _, db_stage_timings = await msg_repo.save_message_with_timings(
                        text=event.text,
                        user_id=user.id,
                        room_id=None
                    )
                    db_save_at = time.perf_counter()
                    
                    await manager.broadcast({
                        "type": "message",
                        "client_id": client_id,
                        "text": event.text,
                        "online_count": manager.count()
                    })
                    broadcast_at = time.perf_counter()
                    
                    log_message_latency(client_id, f"room:{pin}", receive_at, db_save_at, broadcast_at, db_stage_timings=db_stage_timings)

                queued_message = QueuedMessage(
                    text = event.text,
                    user_id = user.id,
                    room_id = room_id,
                )
                
                try: 
                    message_queue.enqueue(queued_message)
                except Exception:
                    logging.exception("Failed to enqueue message")
                    await manager.send_to(client_id, {
                        "type": "Error",
                        "error": "Message delivered, but not queued"
                    })
                    continue
                
    except WebSocketDisconnect:
        pin = manager.get_client_room(client_id)
        if pin:
            await manager.broadcast_to_room(pin, {
                "type": "system",
                "text": f"{client_id} disconnected",
                "room_pin": pin,
                "online_count": manager.get_room_count(pin) - 1
            }, exclude=client_id)
        else:
            await manager.broadcast({
                "type": "system",
                "text": f"{client_id} disconnected"
            }, exclude=client_id)
            
    finally:
        manager.disconnect(client_id)