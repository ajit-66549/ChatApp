from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from connection_manager import ConnectionManager, manager
from schemas import IncomingMessage, OutgoingMessage
from pydantic import ValidationError
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI(title=os.getenv("APP_NAME", "ChatApp"))

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
def health():
    return {"status": "ok"}

@app.get("/clients")
def clients():
    return {
        "count": manager.count(),
        "client_id": manager.get_client_ids()
    }
    
@app.websocket("/ws/{client_id}")
async def websocket_endpoints(websocket: WebSocket, client_id: str):
    connected = await manager.connect(client_id, websocket)
    if not connected:
        return
    
    await manager.broadcast({
        "type": "system",
        "text": f"{client_id} joined the chat",
        "online_count": manager.count()
    })
    
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
            elif event.type == "message":
                await manager.broadcast({
                    "type": "message",
                    "client_id": client_id,
                    "text": event.text,
                    "online_count": manager.count()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        
        await manager.broadcast({
            "type": "system",
            "text": f"{client_id} left the chat",
            "online_count": manager.count()
        })