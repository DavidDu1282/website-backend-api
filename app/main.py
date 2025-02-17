from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.api.routes import auth, tarot, llm, root, counsellor
from app.config import settings
from app.core.startup import startup_event

# Initialize FastAPI App
app = FastAPI()

# 🔹 Allow frontend access (Adjust IP based on your setup)
origins = [
    "http://localhost:5173",  # Local frontend (dev mode)
    "http://127.0.0.1:5173",  # Another localhost variation
    f"http://0.0.0.0:5173",  # External server IP
    "http://host.docker.internal:5173",  # Access from Docker on Mac/Windows
    # "*",  # TEMPORARY: Allow everything (for debugging)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"]#, settings.SERVER_IP]
)

# Include API Routes
app.include_router(root.router)
app.include_router(tarot.router, prefix="/api/tarot", tags=["Tarot"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])
app.include_router(counsellor.router, prefix="/api/counsellor")
app.include_router(auth.router, prefix="/api/auth")

# Register startup event
app.add_event_handler("startup", startup_event)
