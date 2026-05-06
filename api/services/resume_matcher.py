"""
Resume matching and relevance scoring service
Uses TF-IDF to calculate similarity between resume and job descriptions
"""

import re
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import nltk
from nltk.corpus import stopwords
import uuid

# Download required NLTK data
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

COMMON_SKILLS = {
    # Programming Languages
    'python', 'javascript', 'typescript', 'java', 'csharp', 'c++', 'cpp', 'go', 'rust', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',
    
    # Frontend
    'react', 'vue', 'angular', 'html', 'css', 'webpack', 'babel', 'next.js', 'nextjs', 'svelte',
    
    # Backend
    'django', 'flask', 'fastapi', 'express', 'nodejs', 'node.js', 'spring', 'asp.net', 'aspnet', 'rails', 'laravel',
    
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'elasticsearch', 'redis', 'cassandra', 'dynamodb', 'firebase',
    
    # DevOps
    'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'jenkins', 'gitlab', 'github', 'terraform', 'ansible',
    
    # Data Science/ML
    'tensorflow', 'pytorch', 'scikit-learn', 'scikit', 'pandas', 'numpy', 'spark', 'hadoop', 'machine learning', 'ml', 'ai', 'nlp', 'computer vision',
    
    # Other Tools
    'git', 'linux', 'unix', 'rest', 'graphql', 'soap', 'microservices', 'agile', 'scrum', 'jira', 'confluence',
}

class ResumeMatcher:
    """Service for calculating resume-to-job relevance scores"""
    
    def __init__(self, resume_content: str):
        """Initialize matcher with resume content"""
        self.resume_content = resume_content.lower()
        self.resume_skills = self.extract_skills(resume_content)
        self.resume_text_processed = self._preprocess_text(resume_content)
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from text"""
        text = text.lower()
        found_skills = []
        
        for skill in COMMON_SKILLS:
            # Look for whole word matches (with word boundaries)
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text):
                found_skills.append(skill)
        
        return list(set(found_skills))  # Remove duplicates
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for TF-IDF"""
        text = text.lower()
        # Remove special characters and extra whitespace
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def calculate_relevance_score(self, job_title: str, job_description: str) -> Dict:
        """
        Calculate relevance score (0-100) between resume and job
        Returns score, matching skills, missing skills, and explanation
        """
        job_text = f"{job_title} {job_description}".lower() if job_description else job_title.lower()
        job_text_processed = self._preprocess_text(job_text)
        job_skills = self.extract_skills(job_text)
        
        # Calculate skill overlap
        matching_skills = list(set(self.resume_skills) & set(job_skills))
        missing_skills = list(set(job_skills) - set(self.resume_skills))
        
        # TF-IDF Similarity
        try:
            vectorizer = TfidfVectorizer(
                analyzer='char',
                ngram_range=(2, 3),
                lowercase=True,
                stop_words='english'
            )
            
            # Handle case where texts might be very short
            if len(self.resume_text_processed.split()) < 5 or len(job_text_processed.split()) < 5:
                tfidf_score = 0
            else:
                tfidf_matrix = vectorizer.fit_transform([self.resume_text_processed, job_text_processed])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
                tfidf_score = float(similarity[0][0]) * 100
        except:
            tfidf_score = 0
        
        # Skill-based score (0-40)
        if job_skills:
            skill_score = (len(matching_skills) / len(job_skills)) * 40
        else:
            skill_score = 20  # Default if no skills found in job description
        
        # Combined score
        final_score = min(100, (tfidf_score * 0.5) + skill_score)
        
        # Generate explanation
        explanation = self._generate_explanation(
            final_score,
            len(matching_skills),
            len(missing_skills),
            len(job_skills)
        )
        
        return {
            "score": round(final_score, 1),
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "explanation": explanation,
            "skill_match_percentage": round((len(matching_skills) / max(len(job_skills), 1)) * 100, 1)
        }
    
    def _generate_explanation(self, score: float, matching: int, missing: int, total_skills: int) -> str:
        """Generate human-readable explanation of the score"""
        if score >= 80:
            return f"Excellent match! You have {matching} of the {total_skills} required skills."
        elif score >= 60:
            return f"Good match! You have {matching} of {total_skills} required skills, but missing {missing}."
        elif score >= 40:
            return f"Moderate match. You have {matching} matching skills but need to develop {missing} more."
        else:
            return f"Low match. Only {matching} of {total_skills} required skills found."
    
    def calculate_bulk_scores(self, jobs: List[Dict]) -> List[Dict]:
        """Calculate relevance scores for multiple jobs"""
        results = []
        
        for job in jobs:
            job_id = job.get("job_id")
            title = job.get("title", "")
            description = job.get("description", "")
            
            score_data = self.calculate_relevance_score(title, description)
            results.append({
                "job_id": job_id,
                "score": score_data["score"],
                "matching_skills": score_data["matching_skills"],
                "missing_skills": score_data["missing_skills"],
                "explanation": score_data["explanation"]
            })
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except ImportError:
        raise ImportError("PyPDF2 is required for PDF parsing. Install with: pip install PyPDF2")


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file"""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    except ImportError:
        raise ImportError("python-docx is required for DOCX parsing. Install with: pip install python-docx")


def extract_resume_text(file_path: str) -> str:
    """
    Extract text from resume file (supports PDF, DOCX, TXT)
    """
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError("Unsupported file format. Supported: PDF, DOCX, TXT")


def generate_resume_id() -> str:
    """Generate unique resume ID"""
    return f"resume_{uuid.uuid4().hex[:12]}"
