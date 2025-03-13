# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.api.routes import auth_routes, counsellor_routes, llm_routes, root_routes, tarot_routes, bagua_routes
from app.config import settings
from app.core.startup import startup_event  # Import the startup event

# Initialize FastAPI App
app = FastAPI()

# 🔹 Allow frontend access (Adjust IP based on your setup)
origins = [
    "http://localhost:5173",  # Local frontend (dev mode)
    "http://127.0.0.1:5173",  # Another localhost variation
    f"http://0.0.0.0:5173",  # External server IP
    "http://host.docker.internal:5173",  # Access from Docker on Mac/Windows
    "https://140.245.56.252",
    "http://nginx",  # ✅ Add Nginx as a valid origin (Docker internal network)
    "http://backend",  # ✅ Add backend service name if accessed from Nginx
    "http://hao123.ddns.net",  # ADDED: Your domain - HTTP
    "https://hao123.ddns.net", # ADDED: Your domain - HTTPS
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
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "backend", "nginx", "140.245.56.252", "hao123.ddns.net"]#, settings.SERVER_IP]
)

# Include API Routes
app.include_router(root_routes.router)
app.include_router(tarot_routes.router, prefix="/api/tarot", tags=["Tarot"])
app.include_router(llm_routes.router, prefix="/api/llm", tags=["LLM"])
app.include_router(counsellor_routes.router, prefix="/api/counsellor")
app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(bagua_routes.router, prefix="/api/bagua")

# Register startup event
@app.on_event("startup")
async def app_startup():
    await startup_event(app)