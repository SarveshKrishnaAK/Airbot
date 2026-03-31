from pydantic import BaseModel
from typing import Optional


class ChatResponse(BaseModel):
    answer: str
    conversation_id: Optional[int] = None
