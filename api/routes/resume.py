"""
Resume endpoints - Upload and manage resumes
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Body
from typing import List, Dict
import os
import uuid
from api import models, database
from api.services.resume_matcher import ResumeMatcher, generate_resume_id, extract_resume_text

router = APIRouter()

UPLOAD_DIR = "/tmp/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Supported file types
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}

@router.post("/upload", response_model=models.ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    name: str = Form(default="My Resume")
):
    """Upload a resume file (TXT, PDF, or DOCX)"""
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    try:
        # Save file
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Extract text from file
        resume_text = extract_resume_text(file_path)
        
        # Extract skills
        matcher = ResumeMatcher(resume_text)
        skills = matcher.extract_skills(resume_text)
        
        # Save to database
        resume_id = generate_resume_id()
        resume_data = await database.save_resume(
            resume_id=resume_id,
            filename=file.filename,
            content=resume_text,
            extracted_skills=skills
        )
        
        return {
            "resume_id": resume_id,
            "filename": file.filename,
            "extracted_skills": skills,
            "extracted_experience": "See full resume content",
            "uploaded_at": resume_data["uploaded_at"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")
    
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/all", response_model=List[models.ResumeResponse])
async def get_all_resumes():
    """Get all past uploaded resumes"""
    resumes = await database.get_all_resumes()
    return [{
        "resume_id": r["resume_id"],
        "filename": r["filename"],
        "extracted_skills": r.get("extracted_skills", []),
        "extracted_experience": r.get("content", "")[:500],
        "uploaded_at": r["uploaded_at"]
    } for r in resumes]

@router.get("/latest")
async def get_latest_resume():
    """Get the most recently uploaded resume"""
    resume = await database.get_latest_resume()
    
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    return {
        "resume_id": resume["resume_id"],
        "filename": resume["filename"],
        "extracted_skills": resume["extracted_skills"],
        "extracted_experience": resume.get("content", "")[:500],
        "uploaded_at": resume["uploaded_at"]
    }


@router.get("/{resume_id}", response_model=models.ResumeResponse)
async def get_resume(resume_id: str):
    """Get resume details"""
    resume = await database.get_resume(resume_id)
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "resume_id": resume["resume_id"],
        "filename": resume["filename"],
        "extracted_skills": resume["extracted_skills"],
        "extracted_experience": resume.get("content", "")[:500],  # First 500 chars
        "uploaded_at": resume["uploaded_at"]
    }

@router.post("/analyze-relevance")
async def analyze_resume_relevance(resume_id: str):
    """
    Analyze resume and calculate relevance scores for all scraped jobs.
    Only jobs with a description (scraped > 0) are scored.
    """
    import traceback
    resume = await database.get_resume(resume_id)

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_text = resume.get("content", "")
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume content is empty")

    try:
        matcher = ResumeMatcher(resume_text)

        # Only fetch fully-scraped jobs that have a description
        # Skip company-name enrichment (not needed for scoring) — much faster
        jobs = await database.get_scraped_jobs_for_analysis(limit=5000)

        if not jobs:
            return {
                "resume_id": resume_id,
                "total_jobs_analyzed": 0,
                "average_relevance_score": 0,
                "high_matches": 0,
                "top_matches": [],
                "extracted_skills": resume.get("extracted_skills", []),
                "message": "No scraped jobs found. Run details_retriever.py first."
            }

        # Score all jobs (bulk TF-IDF — single matrix operation)
        scores = matcher.calculate_bulk_scores(jobs)

        # Persist scores using bulk_write (fast — single round-trip)
        await database.save_relevance_scores_bulk(resume_id, scores)

        # Stats
        top_scores = scores[:10]
        avg_score  = sum(s["score"] for s in scores) / len(scores) if scores else 0
        high_matches = sum(1 for s in scores if s["score"] >= 70)

        return {
            "resume_id": resume_id,
            "total_jobs_analyzed": len(scores),
            "average_relevance_score": round(avg_score, 1),
            "high_matches": high_matches,
            "top_matches": top_scores,
            "extracted_skills": resume.get("extracted_skills", [])
        }

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[analyze-relevance] ERROR:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error analyzing resume: {str(e)}")


@router.get("/text/{resume_id}")
async def get_resume_text(resume_id: str):
    """Get full resume text"""
    resume = await database.get_resume(resume_id)
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "resume_id": resume_id,
        "content": resume.get("content", ""),
        "filename": resume["filename"]
    }

@router.post("/evaluate-custom-job")
async def evaluate_custom_job(request: models.CustomJobEvaluationRequest):
    """Evaluate a custom pasted job description against the uploaded resume."""
    resume = await database.get_resume(request.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_text = resume.get("content", "")
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume content is empty")
        
    try:
        matcher = ResumeMatcher(resume_text)
        result = matcher.calculate_relevance_score("Custom Job", request.job_description)
        return result
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[evaluate-custom] ERROR:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error evaluating job: {str(e)}")
