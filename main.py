from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
import os
import uuid
from datetime import datetime, timedelta

app = FastAPI()


# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Environment Variables
PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
LOCATION = os.getenv("GOOGLE_REGION", "us-central1")

if not PROJECT_ID:
    raise RuntimeError("Environment variable GOOGLE_PROJECT_ID must be set.")

# Store chat sessions
chat_sessions = {}
session_expiry_time = timedelta(hours=1)  # Set session expiry time


@app.on_event("startup")
async def startup_event():
    """
    Initialize Vertex AI client on application startup.
    """
    try:
        print("Initializing Vertex AI client...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        print("Vertex AI client initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Vertex AI client: {e}")
        raise RuntimeError("Failed to initialize Vertex AI client.")


class ChatRequest(BaseModel):
    session_id: str
    prompt: str


@app.post("/api/llm/chat")
async def chat(request: ChatRequest):
    """
    Endpoint to handle user chat with session management.
    """
    global chat_sessions
    session_id = request.session_id
    prompt = request.prompt

    try:
        # Check if the session already exists
        if session_id in chat_sessions:
            session_data = chat_sessions[session_id]
            chat_session = session_data["chat_session"]
            session_data["last_used"] = datetime.now()  # Update last used time
        else:
            # Create a new chat session
            model = GenerativeModel("gemini-1.5-flash-002")
            chat_session = model.start_chat()
            chat_sessions[session_id] = {
                "chat_session": chat_session,
                "last_used": datetime.now(),
            }

        # Send message to the chat session
        text_response = []
        responses = chat_session.send_message(prompt, stream=True)
        for chunk in responses:
            text_response.append(chunk.text)

        return {"response": "".join(text_response)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")


@app.on_event("startup")
async def cleanup_sessions():
    """
    Periodically clean up expired sessions.
    """
    global chat_sessions
    current_time = datetime.now()
    expired_sessions = [
        session_id
        for session_id, session_data in chat_sessions.items()
        if current_time - session_data["last_used"] > session_expiry_time
    ]
    for session_id in expired_sessions:
        del chat_sessions[session_id]
        print(f"Session {session_id} expired and removed.")
