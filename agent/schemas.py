from pydantic import BaseModel
from typing import Any, Optional

class ToolResult(BaseModel):
    status: str  # "ok" | "error"
    data: Optional[Any] = None
    error: Optional[str] = None