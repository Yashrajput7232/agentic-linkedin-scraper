"""
FastAPI application for LinkedIn Job Scraper
Provides REST API for job management, resume matching, and scraper control
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file (no-op if already set via Docker/environment)
load_dotenv()

# Add parent directory to path so we can import scripts
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import jobs, resume, scraper
from api import database

# ─── Initialize FastAPI app ──────────────────────────────────────────────────
app = FastAPI(
    title="LinkedIn Job Scraper API",
    description="API for managing LinkedIn job postings with resume matching",
    version="1.0.0"
)

# ─── Startup and Shutdown Events ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB on startup"""
    await database.connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await database.close_mongo_connection()

# ─── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include Routers ──────────────────────────────────────────────────────────
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["Scraper"])

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LinkedIn Job Scraper API"}

# ─── Root redirect to dashboard ───────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """Redirect to dashboard"""
    return {
        "message": "LinkedIn Job Scraper API",
        "dashboard": "/dashboard",
        "docs": "/docs"
    }

# ─── Serve Frontend ───────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    # Mount frontend files
    app.mount("/dashboard", StaticFiles(directory=str(frontend_path), html=True), name="dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

