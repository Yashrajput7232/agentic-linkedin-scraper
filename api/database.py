"""
Database service for MongoDB operations
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, List, Any
import os
from datetime import datetime

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "linkedin_jobs")

mongodb_client: Optional[AsyncIOMotorClient] = None
database = None

async def connect_to_mongo():
    """Connect to MongoDB"""
    global mongodb_client, database
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    database = mongodb_client[DB_NAME]
    print(f"✓ Connected to MongoDB at {MONGODB_URL}")

async def close_mongo_connection():
    """Close MongoDB connection"""
    if mongodb_client:
        mongodb_client.close()
        print("✓ Closed MongoDB connection")

# ─── Jobs Collection ──────────────────────────────────────────────────────────
async def get_jobs(
    filter_dict: Dict[str, Any] = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "original_listed_time",
    sort_order: int = -1
) -> List[Dict]:
    """Get jobs from database with filtering"""
    if not filter_dict:
        filter_dict = {}
    
    collection = database["jobs"]
    cursor = collection.find(filter_dict)
    cursor = cursor.sort(sort_by, sort_order).skip(skip).limit(limit)
    
    return await cursor.to_list(length=limit)

async def get_job_by_id(job_id: str) -> Optional[Dict]:
    """Get a single job by ID"""
    collection = database["jobs"]
    return await collection.find_one({"job_id": job_id})

async def get_jobs_count(filter_dict: Dict = None) -> int:
    """Get total count of jobs"""
    if not filter_dict:
        filter_dict = {}
    
    collection = database["jobs"]
    return await collection.count_documents(filter_dict)

# ─── Resume Collection ───────────────────────────────────────────────────────
async def save_resume(resume_id: str, filename: str, content: str, extracted_skills: List[str]):
    """Save resume to database"""
    collection = database["resumes"]
    resume_data = {
        "resume_id": resume_id,
        "filename": filename,
        "content": content,
        "extracted_skills": extracted_skills,
        "uploaded_at": datetime.utcnow()
    }
    await collection.insert_one(resume_data)
    return resume_data

async def get_resume(resume_id: str) -> Optional[Dict]:
    """Get resume by ID"""
    collection = database["resumes"]
    return await collection.find_one({"resume_id": resume_id})

async def get_latest_resume() -> Optional[Dict]:
    """Get the most recently uploaded resume"""
    collection = database["resumes"]
    return await collection.find_one(sort=[("uploaded_at", -1)])

# ─── Bookmarks Collection ──────────────────────────────────────────────────────
async def add_bookmark(job_id: str, notes: str = None) -> Dict:
    """Bookmark a job"""
    collection = database["bookmarks"]
    bookmark = {
        "job_id": job_id,
        "notes": notes,
        "created_at": datetime.utcnow()
    }
    result = await collection.insert_one(bookmark)
    bookmark["_id"] = result.inserted_id
    return bookmark

async def remove_bookmark(job_id: str) -> bool:
    """Remove a bookmark"""
    collection = database["bookmarks"]
    result = await collection.delete_one({"job_id": job_id})
    return result.deleted_count > 0

async def get_bookmarks(skip: int = 0, limit: int = 50) -> List[Dict]:
    """Get all bookmarked jobs"""
    collection = database["bookmarks"]
    cursor = collection.find().sort("created_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def is_bookmarked(job_id: str) -> bool:
    """Check if a job is bookmarked"""
    collection = database["bookmarks"]
    return await collection.find_one({"job_id": job_id}) is not None

# ─── Relevance Scores Collection ───────────────────────────────────────────
async def save_relevance_scores(resume_id: str, scores: List[Dict]):
    """Save relevance scores for jobs"""
    collection = database["relevance_scores"]
    
    for score in scores:
        await collection.update_one(
            {"resume_id": resume_id, "job_id": score["job_id"]},
            {"$set": {**score, "resume_id": resume_id, "updated_at": datetime.utcnow()}},
            upsert=True
        )

async def get_relevance_score(resume_id: str, job_id: str) -> Optional[Dict]:
    """Get relevance score for a job"""
    collection = database["relevance_scores"]
    return await collection.find_one({"resume_id": resume_id, "job_id": job_id})

async def get_jobs_with_scores(resume_id: str, skip: int = 0, limit: int = 50) -> List[Dict]:
    """Get jobs with relevance scores"""
    collection = database["relevance_scores"]
    cursor = collection.find({"resume_id": resume_id}).sort("score", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

# ─── Scraper Logs Collection ───────────────────────────────────────────────
async def log_scrape_event(event_type: str, details: Dict = None):
    """Log scraper events"""
    collection = database["scraper_logs"]
    log = {
        "event_type": event_type,
        "details": details or {},
        "timestamp": datetime.utcnow()
    }
    await collection.insert_one(log)

async def get_scraper_stats() -> Dict:
    """Get scraper statistics"""
    jobs_collection = database["jobs"]
    
    total_jobs = await jobs_collection.count_documents({})
    jobs_with_details = await jobs_collection.count_documents({"scraped": True})
    pending_jobs = await jobs_collection.count_documents({"scraped": False})
    
    return {
        "jobs_scraped_total": total_jobs,
        "jobs_with_details": jobs_with_details,
        "pending_jobs": pending_jobs
    }
