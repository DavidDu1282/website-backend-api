
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import tarot, llm
from app.config import settings
from app.core.startup import startup_event

# Initialize FastAPI App
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] # to generalize, update list with allowed origins
)

# Include API Routes
app.include_router(tarot.router, prefix="/api/tarot", tags=["Tarot"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])

# Register startup event
app.on_event("startup")(startup_event)
