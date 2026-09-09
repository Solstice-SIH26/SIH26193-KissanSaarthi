from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import tokens, centers, users, voice, webhooks

app = FastAPI(
    title="SIH PS26032 — Procurement Center API",
    description="Token queue, schedule, and MSP price info for farmers, "
                "procurement staff, and admin.",
    version="0.1.0",
)

# Wide-open CORS for the demo so the React frontend can hit this from any
# origin during development. Tighten this (allow_origins=[frontend URL])
# before anything resembling a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tokens.router)
app.include_router(centers.router)
app.include_router(users.router)
app.include_router(voice.router)
app.include_router(webhooks.router)

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
