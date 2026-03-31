from pydantic import BaseModel
from typing import Literal
from typing import Optional


class ChatRequest(BaseModel):
    question: str
    level: str = "engineering"
    mode: Literal["test_case", "general_chat"] = "general_chat"
    conversation_id: Optional[int] = None


class DownloadRequest(BaseModel):
    content: str
    query: str = ""
