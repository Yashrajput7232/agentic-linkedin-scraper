"""
Database service for MongoDB operations
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, List, Any
import os
from datetime import datetime

MONGODB_URL = os.getenv("MONGODB_URI") or os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "linkedin_jobs")

mongodb_client: Optional[AsyncIOMotorClient] = None
database = None
_company_name_cache: Dict[str, str] = {}  # in-memory cache: company_id -> name

async def connect_to_mongo():
    """Connect to MongoDB"""
    global mongodb_client, database
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    database = mongodb_client[DB_NAME]
    print(f"✓ Connected to MongoDB ")

async def close_mongo_connection():
    """Close MongoDB connection"""
    if mongodb_client:
        mongodb_client.close()
        print("✓ Closed MongoDB connection")

# ─── Jobs Collection ──────────────────────────────────────────────────────────
def _normalize_job(job: Dict) -> Dict:
    """Normalize a raw MongoDB job document for API consumption."""
    if job is None:
        return job
    # Strip un-serializable MongoDB ObjectId
    job.pop("_id", None)
    # job_id is stored as int — coerce to str
    if "job_id" in job and not isinstance(job["job_id"], str):
        job["job_id"] = str(job["job_id"])
    # original_listed_time is epoch-ms int — convert to ISO 8601 string
    olt = job.get("original_listed_time")
    if olt is not None and isinstance(olt, (int, float)):
        from datetime import timezone
        job["original_listed_time"] = datetime.fromtimestamp(
            olt / 1000, tz=timezone.utc
        ).isoformat()
    return job

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
    cursor = collection.find(filter_dict, {"_id": 0})
    cursor = cursor.sort(sort_by, sort_order).skip(skip).limit(limit)

    jobs = await cursor.to_list(length=limit)
    
    # Bulk fetch company names
    company_ids = [str(j.get("company_id", "")) for j in jobs]
    company_names = await get_company_names(company_ids)
    
    enriched = []
    for j in jobs:
        j = _normalize_job(j)
        cid = j.get("company_id", "")
        j["company_id"] = company_names.get(cid, cid)
        enriched.append(j)
    return enriched

# ─── Company Lookup ─────────────────────────────────────────────────────────
async def get_company_names(company_ids: List[str]) -> Dict[str, str]:
    """Resolve a list of company_ids to names in bulk."""
    missing = []
    result = {}
    for cid in company_ids:
        if not cid: continue
        if cid in _company_name_cache:
            result[cid] = _company_name_cache[cid]
        else:
            missing.append(cid)
            result[cid] = cid # default to ID
    
    if missing:
        try:
            collection = database["companies"]
            cursor = collection.find({"company_id": {"$in": missing}}, {"_id": 0, "company_id": 1, "name": 1})
            docs = await cursor.to_list(length=None)
            for doc in docs:
                doc_cid = doc.get("company_id")
                name = doc.get("name", doc_cid)
                result[doc_cid] = name
                _company_name_cache[doc_cid] = name
        except Exception:
            pass
    return result

async def get_company_name(company_id: str) -> str:
    """Resolve company_id to a human-readable company name."""
    if not company_id:
        return "Unknown Company"
    if company_id in _company_name_cache:
        return _company_name_cache[company_id]
    try:
        collection = database["companies"]
        doc = await collection.find_one({"company_id": company_id}, {"_id": 0, "name": 1})
        name = doc.get("name", company_id) if doc else company_id
    except Exception:
        name = company_id
    _company_name_cache[company_id] = name
    return name


async def get_job_by_id(job_id: str) -> Optional[Dict]:
    """Get a single job by ID — tries both str and int forms."""
    collection = database["jobs"]
    # Try string form first, then int (for legacy int-keyed docs)
    job = await collection.find_one({"job_id": job_id}, {"_id": 0})
    if job is None:
        try:
            job = await collection.find_one({"job_id": int(job_id)}, {"_id": 0})
        except (ValueError, TypeError):
            pass
    job = _normalize_job(job)
    if job:
        job["company_id"] = await get_company_name(job.get("company_id", ""))
    return job

async def get_relevant_jobs(resume_id: str, skip: int = 0, limit: int = 50) -> List[Dict]:
    """Get jobs enriched with relevance scores, sorted by score desc."""
    scores_coll = database["relevance_scores"]
    cursor = scores_coll.find({"resume_id": resume_id}, {"_id": 0}).sort("score", -1).skip(skip).limit(limit)
    score_docs = await cursor.to_list(length=limit)

    result = []
    for s in score_docs:
        job = await get_job_by_id(s["job_id"])
        if job:
            job["relevance_score"] = s.get("score", 0)
            job["matching_skills"] = s.get("matching_skills", [])
            result.append(job)
    return result

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

async def get_all_resumes() -> List[Dict]:
    """Get all uploaded resumes, sorted by newest first"""
    collection = database["resumes"]
    cursor = collection.find({}, {"_id": 0, "content": 0}).sort("uploaded_at", -1)
    return await cursor.to_list(length=100)

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

async def are_bookmarked(job_ids: List[str]) -> Dict[str, bool]:
    """Check if multiple jobs are bookmarked in one query."""
    if not job_ids:
        return {}
    collection = database["bookmarks"]
    cursor = collection.find({"job_id": {"$in": job_ids}}, {"_id": 0, "job_id": 1})
    bookmarked_docs = await cursor.to_list(length=None)
    bookmarked_ids = {doc["job_id"] for doc in bookmarked_docs}
    return {jid: (jid in bookmarked_ids) for jid in job_ids}

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
