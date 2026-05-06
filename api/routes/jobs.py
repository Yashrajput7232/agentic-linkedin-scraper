"""
Jobs endpoints - List, filter, and manage jobs
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from api import models, database
from api.services.resume_matcher import ResumeMatcher

router = APIRouter()

@router.get("/", response_model=List[models.JobWithDetails])
async def list_jobs(
    location: Optional[str] = Query(None),
    work_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    min_salary: Optional[float] = Query(None),
    max_salary: Optional[float] = Query(None),
    remote_only: bool = Query(False),
    search: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    sort_by: str = Query("original_listed_time"),
    sort_order: str = Query("descending"),
):
    """List jobs with optional filtering"""
    
    # Build filter dictionary
    filter_dict = {}
    
    if location:
        filter_dict["location"] = {"$regex": location, "$options": "i"}
    
    if work_type:
        filter_dict["formatted_work_type"] = work_type
    
    if experience_level:
        filter_dict["formatted_experience_level"] = experience_level
    
    if remote_only:
        filter_dict["remote_allowed"] = True
    
    if min_salary or max_salary:
        salary_filter = {}
        if min_salary:
            salary_filter["$gte"] = min_salary
        if max_salary:
            salary_filter["$lte"] = max_salary
    
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        filter_dict["$or"] = [
            {"title": search_regex},
            {"description": search_regex},
        ]
    
    # Determine sort order
    sort_order_int = -1 if sort_order == "descending" else 1
    
    # Validate sort field
    valid_sort_fields = ["original_listed_time", "title", "location", "min_salary"]
    if sort_by not in valid_sort_fields:
        sort_by = "original_listed_time"
    
    try:
        jobs = await database.get_jobs(
            filter_dict=filter_dict,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order_int
        )
        
        # Add bookmark status in bulk
        job_ids = [str(job.get("job_id")) for job in jobs if job.get("job_id")]
        bookmarked_map = await database.are_bookmarked(job_ids)
        for job in jobs:
            job["is_bookmarked"] = bookmarked_map.get(str(job.get("job_id")), False)
        
        return jobs
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")


@router.get("/relevant", response_model=List[models.JobWithDetails])
async def get_relevant_jobs(
    resume_id: Optional[str] = Query(None, description="Specific resume ID to use for relevance"),
    skip: int = Query(0),
    limit: int = Query(50),
):
    """Return jobs sorted by resume relevance score (requires resume to be analyzed first)."""
    if not resume_id:
        # Get latest resume
        resume = await database.get_latest_resume()
        if not resume:
            raise HTTPException(
                status_code=400,
                detail="No resume uploaded. Upload a resume and run 'Analyze' first."
            )
        resume_id = resume["resume_id"]

    jobs = await database.get_relevant_jobs(resume_id, skip=skip, limit=limit)

    if not jobs:
        raise HTTPException(
            status_code=404,
            detail="No relevance scores found. Click 'Analyze & Calculate Relevance Scores' in the Resume tab first."
        )

    # Add bookmark status in bulk
    job_ids = [str(job.get("job_id")) for job in jobs if job.get("job_id")]
    bookmarked_map = await database.are_bookmarked(job_ids)
    for job in jobs:
        job["is_bookmarked"] = bookmarked_map.get(str(job.get("job_id")), False)

    return jobs


@router.get("/{job_id}", response_model=models.JobWithDetails)
async def get_job(job_id: str):
    """Get a single job by ID"""
    job = await database.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job["is_bookmarked"] = await database.is_bookmarked(job_id)
    return job


@router.post("/bookmark/{job_id}")
async def bookmark_job(job_id: str, notes: Optional[str] = Query(None)):
    """Bookmark a job"""
    job = await database.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if already bookmarked
    if await database.is_bookmarked(job_id):
        raise HTTPException(status_code=400, detail="Job is already bookmarked")
    
    bookmark = await database.add_bookmark(job_id, notes)
    return {"message": "Job bookmarked successfully", "bookmark_id": str(bookmark.get("_id"))}


@router.delete("/bookmark/{job_id}")
async def remove_bookmark(job_id: str):
    """Remove a bookmark"""
    success = await database.remove_bookmark(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {"message": "Bookmark removed successfully"}


@router.get("/bookmarks/all", response_model=List[models.BookmarkResponse])
async def get_bookmarks(skip: int = Query(0), limit: int = Query(50)):
    """Get all bookmarked jobs"""
    bookmarks = await database.get_bookmarks(skip=skip, limit=limit)
    
    result = []
    for bookmark in bookmarks:
        job = await database.get_job_by_id(bookmark.get("job_id"))
        if job:
            result.append({
                "bookmark_id": str(bookmark.get("_id")),
                "job_id": job.get("job_id"),
                "job_title": job.get("title"),
                "company": job.get("company_name", job.get("company_id")),
                "notes": bookmark.get("notes"),
                "created_at": bookmark.get("created_at")
            })
    
    return result


@router.get("/relevance/scores", response_model=List[models.RelevanceScoreResponse])
async def get_job_scores_with_resume(
    skip: int = Query(0),
    limit: int = Query(50)
):
    """Get jobs sorted by relevance score (requires resume)"""
    
    # Get latest resume
    resume = await database.get_latest_resume()
    if not resume:
        raise HTTPException(
            status_code=400,
            detail="No resume uploaded. Please upload a resume first."
        )
    
    resume_id = resume.get("resume_id")
    
    # Get jobs with scores
    jobs_with_scores = await database.get_jobs_with_scores(resume_id, skip, limit)
    
    # Enrich with job details
    result = []
    for score_data in jobs_with_scores:
        job = await database.get_job_by_id(score_data.get("job_id"))
        if job:
            result.append({
                "job_id": job.get("job_id"),
                "title": job.get("title"),
                "score": score_data.get("score"),
                "matching_skills": score_data.get("matching_skills", []),
                "missing_skills": score_data.get("missing_skills", []),
                "explanation": score_data.get("explanation", "")
            })
    
    return result


@router.post("/calculate-relevance")
async def calculate_relevance_for_jobs(
    request: models.RelevanceScoreRequest
):
    """Calculate relevance scores for specific jobs"""
    
    resume = await database.get_resume(request.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    resume_content = resume.get("content")
    matcher = ResumeMatcher(resume_content)
    
    # Get jobs to score
    if request.job_ids:
        jobs = []
        for job_id in request.job_ids:
            job = await database.get_job_by_id(job_id)
            if job:
                jobs.append(job)
    else:
        # Get all jobs
        jobs = await database.get_jobs(limit=1000)
    
    # Calculate scores
    scores = matcher.calculate_bulk_scores(jobs)
    
    # Save scores to database
    await database.save_relevance_scores(request.resume_id, scores)
    
    return {
        "resume_id": request.resume_id,
        "jobs_scored": len(scores),
        "top_matches": scores[:10]  # Return top 10
    }


