"""
Resume endpoints - Upload and manage resumes
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import List
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


@router.post("/analyze-relevance")
async def analyze_resume_relevance(resume_id: str):
    """
    Analyze resume and calculate relevance scores for all jobs
    """
    resume = await database.get_resume(resume_id)
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    try:
        resume_text = resume.get("content")
        matcher = ResumeMatcher(resume_text)
        
        # Get all jobs from database
        jobs = await database.get_jobs(limit=10000)
        
        # Calculate scores for all jobs
        scores = matcher.calculate_bulk_scores(jobs)
        
        # Save scores
        await database.save_relevance_scores(resume_id, scores)
        
        # Return statistics
        top_scores = scores[:10]
        avg_score = sum(s["score"] for s in scores) / len(scores) if scores else 0
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
