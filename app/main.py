# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import (
    auth_routes,
    bagua_routes,
    counsellor_routes,
    llm_routes,
    root_routes,
    tarot_routes,
)
from app.config import settings
from app.core.startup import startup_event

app = FastAPI()

origins = [
    "http://localhost",
    "http://0.0.0.0",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
    "http://host.docker.internal:5173",
    "https://140.245.56.252",
    "http://nginx",
    "http://backend",
    "http://hao123.ddns.net",
    "https://hao123.ddns.net",
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

app.include_router(root_routes.router)
app.include_router(tarot_routes.router, prefix="/api/tarot", tags=["Tarot"])
app.include_router(llm_routes.router, prefix="/api/llm", tags=["LLM"])
app.include_router(counsellor_routes.router, prefix="/api/counsellor")
app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(bagua_routes.router, prefix="/api/bagua")

@app.on_event("startup")
async def app_startup():
    await startup_event(app)