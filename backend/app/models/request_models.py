from pydantic import BaseModel
from typing import Literal


class ChatRequest(BaseModel):
    question: str
    level: str = "engineering"
    mode: Literal["test_case", "general_chat"] = "general_chat"


class DownloadRequest(BaseModel):
    content: str
    query: str = ""
