# Standard Library Imports
import os
import json
from datetime import datetime, timedelta

# Third-Party Library Imports
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex

# Vertex AI Imports
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession


app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://david-portfolio-website-navy-eight.vercel.app/"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Environment Variables
PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
LOCATION = os.getenv("GOOGLE_REGION", "us-central1")
if not PROJECT_ID:
    raise RuntimeError("Environment variable GOOGLE_PROJECT_ID must be set.")

# Annoy and SentenceTransformer Setup
INDEX_FILE = "chunks.ann"
CSV_FILE = "chunks_mapping.csv"
MODEL_NAME = "all-MiniLM-L6-v2"

# Globals
annoy_index = None
chunks = None
embedding_model = None
chat_sessions = {}
session_expiry_time = timedelta(hours=1)  # Session expiry time


@app.on_event("startup")
async def startup_event():
    """
    Initialize resources on application startup.
    """
    global annoy_index, chunks, embedding_model
    try:
        print("Initializing Vertex AI client...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        print("Vertex AI client initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Vertex AI client: {e}")
        raise RuntimeError("Failed to initialize Vertex AI client.")

    # Load the Annoy index
    annoy_index = AnnoyIndex(384, "angular")
    annoy_index.load(INDEX_FILE)

    # Load the chunks mapping
    with open(CSV_FILE, "r") as f:
        chunks = {int(line.split(",")[0]): ",".join(line.split(",")[1:]).strip() for line in f}

    # Load the embedding model
    embedding_model = SentenceTransformer(MODEL_NAME)
    print("Resources loaded successfully.")


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


class ChatRequest(BaseModel):
    session_id: str
    prompt: str


@app.post("/api/llm/query_and_chat")
async def query_and_chat(request: ChatRequest, k: int = 5):
    """
    Query the Annoy index for relevant chunks and include them in the LLM chat response.
    """
    global chat_sessions, annoy_index, embedding_model, chunks

    session_id = request.session_id
    prompt = request.prompt

    try:
        # Generate the embedding for the query
        query_embedding = embedding_model.encode(prompt)

        # Retrieve top-k nearest neighbors
        indices = annoy_index.get_nns_by_vector(query_embedding, k, include_distances=False)

        # Retrieve corresponding text chunks
        relevant_chunks = "\n".join([chunks[idx] for idx in indices])

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

        # Construct a prompt that includes the retrieved chunks
        augmented_prompt = (
            f"The following context might help answer the question:\n{relevant_chunks}\n\n{prompt}"
        )

        # Send the augmented prompt to the chat session
        text_response = []
        responses = chat_session.send_message(augmented_prompt, stream=True)
        for chunk in responses:
            text_response.append(chunk.text)

        return {"response": "".join(text_response)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process query and chat: {str(e)}")


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


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