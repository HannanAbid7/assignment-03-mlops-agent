from fastapi import FastAPI
from pydantic import BaseModel
from agent.orchestrator import handle_request

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    return {"response": handle_request(req.message)}