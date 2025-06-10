from pydantic import BaseModel
from typing import List, Optional, Literal, Dict

class Message(BaseModel):
    sender: Literal["user", "llm", "system"] # "system" for potential future use in history
    text: str

class FileAttachment(BaseModel):
    filename: str
    content: str
    content_type: str

class ChatMessageRequest(BaseModel):
    text: str
    temperature: float = 0.7
    history: Optional[List[Message]] = None
    attachments: Optional[List[FileAttachment]] = None
    enabled_tools: Optional[List[str]] = None  # List of enabled tool names
    system_prompt: Optional[str] = None

class ChatMessageResponse(BaseModel):
    text: str
    error: str | None = None 