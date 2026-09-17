from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.graph import run_agent_turn
from agent.prompts import SYSTEM_PROMPT


app = FastAPI(
    title="D2C AI Operations Agent",
    description="API for the D2C customer support agent.",
    version="1.0.0"
)

# Serve the frontend files from the same FastAPI application.
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    agent_steps: list
    iterations: int
    completed: bool


# Store conversation history separately for each session.
sessions = {}


@app.get("/")
def root():
    # Serve the chat interface from the same FastAPI application.
    return FileResponse(
        Path("static") / "index.html"
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Start a new conversation the first time a session is used.
    if request.session_id not in sessions:
        sessions[request.session_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    messages = sessions[request.session_id]

    # Send one user message through the agent while keeping
    # the conversation history for future follow-up messages.
    result = run_agent_turn(
        messages,
        request.message
    )

    # Pass the complete agent result to the frontend, including
    # the tool activity used to generate the response.
    return result