from pydantic import BaseModel
from typing import Optional, Literal

# message from client to server
class IncomingMessage(BaseModel):
    type: Literal["message", "ping"]
    text: Optional[str] = None
   
# message from server to client 
class OutgoingMessage(BaseModel):
    type: str
    text: Optional[str] = None
    client_id: Optional[str] = None
    online_count: Optional[int] = None