from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.api.routes import auth, tarot, llm, root, counsellor
from app.config import settings
# from app.core.security import limiter <-- removed, not needed with this in-memory approach
from app.core.startup import startup_event  # Correct import

# Initialize FastAPI App
app = FastAPI()

SERVER_IP = "140.245.56.252"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{SERVER_IP}",  # Allow frontend hosted on this IP
        "http://localhost:5173",  # Allow local development
        "http://127.0.0.1:5173",  # Allow local React frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=[SERVER_IP, "localhost", "127.0.0.1"]
)

# Include API Routes
app.include_router(root.router)
app.include_router(tarot.router, prefix="/api/tarot", tags=["Tarot"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])
app.include_router(counsellor.router, prefix="/api/counsellor")
app.include_router(auth.router, prefix="/api/auth")


# Register startup event.  This is the correct way to register an async startup.
app.add_event_handler("startup", startup_event)  # Use add_event_handler
