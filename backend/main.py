from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from connection_manager import ConnectionManager
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

manager = ConnectionManager()

@app.get("/")
def root():
    return {"message": "ChatApp backend is running."}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoints(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = {
                "type": "message",
                "client_id": client_id,
                "text": payload.get("text", ""),
            }
            await manager.broadcast(json.dumps(message))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        leave_msg = json.dumps({
            "type": "system",
            "text": f"{client_id} left the chat"
        })
        await manager.broadcast(leave_msg)