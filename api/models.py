"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ─── Job Models ──────────────────────────────────────────────────────────────
class JobBase(BaseModel):
    title: str
    description: str
    company_id: Optional[str] = None
    location: Optional[str] = None
    job_posting_url: Optional[str] = None
    
class JobResponse(JobBase):
    job_id: str
    relevance_score: Optional[float] = None
    is_bookmarked: bool = False

    class Config:
        from_attributes = True

class JobWithDetails(JobResponse):
    company_name: Optional[str] = None       # resolved from companies collection
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    formatted_work_type: Optional[str] = None
    formatted_experience_level: Optional[str] = None
    remote_allowed: Optional[bool] = None
    original_listed_time: Optional[str] = None
    skills_desc: Optional[str] = None
    matching_skills: Optional[List[str]] = None  # populated when sorted by relevance

# ─── Resume Models ──────────────────────────────────────────────────────────
class ResumeUpload(BaseModel):
    filename: str
    content: str

class ResumeResponse(BaseModel):
    resume_id: str
    filename: str
    extracted_skills: List[str]
    extracted_experience: str
    uploaded_at: datetime

# ─── Bookmark Models ────────────────────────────────────────────────────────
class BookmarkCreate(BaseModel):
    job_id: str
    notes: Optional[str] = None

class BookmarkResponse(BaseModel):
    bookmark_id: str
    job_id: str
    job_title: str
    company: Optional[str] = None
    relevance_score: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

# ─── Scraper Models ────────────────────────────────────────────────────────
class ScraperStatus(BaseModel):
    is_running: bool
    last_run: Optional[datetime] = None
    jobs_scraped_total: int
    jobs_with_details: int
    pending_jobs: int

class ScrapeTrigger(BaseModel):
    search_terms: List[str] = Field(default=[], description="Optional search terms to use")
    full_details: bool = Field(default=False, description="Whether to fetch full job details")

# ─── Filter Models ──────────────────────────────────────────────────────────
class JobFilterParams(BaseModel):
    location: Optional[str] = None
    work_type: Optional[str] = None
    experience_level: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    remote_only: bool = False
    skip: int = 0
    limit: int = 50
    sort_by: str = Field(default="relevance_score", description="Field to sort by")
    sort_order: str = Field(default="descending", description="ascending or descending")

# ─── Relevance Score Models ────────────────────────────────────────────────
class RelevanceScoreRequest(BaseModel):
    resume_id: str
    job_ids: Optional[List[str]] = None

class RelevanceScoreResponse(BaseModel):
    job_id: str
    title: str
    score: float
    matching_skills: List[str]
    missing_skills: List[str]
    explanation: str
