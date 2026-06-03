"""
bio-horizon API — Entry point.
All route logic lives in api/routes/. This file only wires things together.
"""

# Environment & encoding must be configured before any other import
from config.config import setup_encoding, patch_json_ascii, setup_logging, setup_huggingface_token, get_cors_origins
setup_encoding()
patch_json_ascii()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router

setup_logging()
setup_huggingface_token()  # Configure HF token for OpenMed models

# =============================================================================
# Create FastAPI app
# =============================================================================

app = FastAPI(title="bio-horizon API", version="1.0.0")
print("[startup] FastAPI app initialized")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Mount routers
# =============================================================================

# Main API router (health, ask, upload, kg, pubmed, ner, cache, conversations, users, topics, jobs)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    print("[startup] Starting uvicorn server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)