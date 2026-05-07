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
        self.resume_experience_years = self.extract_experience_years(resume_content, is_resume=True)

    def extract_experience_years(self, text: str, is_resume: bool = False) -> float:
        """Extract years of experience from text"""
        text = text.lower()
        if is_resume:
            # Exclude internship experience
            lines = re.split(r'[\n\.]', text)
            filtered_text = " ".join([line for line in lines if 'intern' not in line])
            
            # 1. Try explicit "X years"
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:\+|to|-|–)?\s*(?:\d+)?\s*years?(?:\s+of)?\s+experience', filtered_text)
            explicit_years = max([float(m) for m in matches if 0 < float(m) < 40], default=0.0)
            
            # 2. Try date ranges
            import datetime
            current_year = datetime.datetime.now().year
            total_years_dates = 0.0
            date_matches = re.findall(r'\b(19\d{2}|20\d{2})\s*(?:-|to|–|—)\s*(20\d{2}|present|current|now)\b', filtered_text)
            intervals = []
            for start_str, end_str in date_matches:
                start_yr = int(start_str)
                end_yr = current_year if end_str in ['present', 'current', 'now'] else int(end_str)
                if start_yr <= end_yr <= current_year:
                    intervals.append((start_yr, end_yr))
            
            if intervals:
                intervals.sort()
                consolidated = [intervals[0]]
                for curr in intervals[1:]:
                    prev = consolidated[-1]
                    if curr[0] <= prev[1]:
                        consolidated[-1] = (prev[0], max(prev[1], curr[1]))
                    else:
                        consolidated.append(curr)
                for interval in consolidated:
                    total_years_dates += max(0.5, interval[1] - interval[0])
            
            return max(explicit_years, total_years_dates)
        else:
            # For job descriptions, we want minimum required years
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:\+|to|-|–)?\s*(?:\d+)?\s*years?(?:\s+of)?\s+experience', text)
            if matches:
                nums = [float(m) for m in matches if 0 < float(m) < 20]
                if nums:
                    return min(nums)
            
            # fallback: look for just "years"
            matches2 = re.findall(r'(\d+(?:\.\d+)?)\s*(?:\+|to|-|–)?\s*(?:\d+)?\s*years?', text)
            if matches2:
                nums = [float(m) for m in matches2 if 0 < float(m) < 20]
                if nums:
                    return min(nums)
            return 0.0
    
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
        
        # Experience Check
        job_exp = self.extract_experience_years(job_text, is_resume=False)
        exp_penalty = 0
        if job_exp > 0 and self.resume_experience_years < job_exp:
            gap = job_exp - self.resume_experience_years
            exp_penalty = min(20, (gap / job_exp) * 20)
            final_score = max(0, final_score - exp_penalty)
            
        # Detailed feedback
        pros = []
        cons = []
        
        if matching_skills:
            pros.append(f"You have {len(matching_skills)} of the required skills ({', '.join(matching_skills[:5])}{'...' if len(matching_skills)>5 else ''}).")
        
        if missing_skills:
            cons.append(f"You are missing {len(missing_skills)} recommended skills ({', '.join(missing_skills[:5])}{'...' if len(missing_skills)>5 else ''}).")
        
        if job_exp > 0:
            if self.resume_experience_years >= job_exp:
                pros.append(f"You meet the experience requirement (Requires {job_exp} years, you have ~{self.resume_experience_years} years).")
            else:
                cons.append(f"You may fall short on experience (Requires {job_exp} years, you have ~{self.resume_experience_years} years).")
        else:
            pros.append(f"Your experience (~{self.resume_experience_years} years) looks sufficient as no strict minimum was found.")

        # Generate simple explanation
        explanation = self._generate_explanation(
            final_score + exp_penalty,
            len(matching_skills),
            len(missing_skills),
            len(job_skills)
        )
        if exp_penalty > 0:
            explanation += f" Note: Job asks for {job_exp} years experience, but resume shows ~{self.resume_experience_years} years."
        
        return {
            "score": round(final_score, 1),
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "explanation": explanation,
            "skill_match_percentage": round((len(matching_skills) / max(len(job_skills), 1)) * 100, 1),
            "pros": pros,
            "cons": cons,
            "job_experience_required": job_exp,
            "candidate_experience": self.resume_experience_years
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
        """Calculate relevance scores for multiple jobs in bulk for performance"""
        results = []
        
        # Pre-process all jobs text
        job_texts = []
        job_skills_list = []
        for job in jobs:
            title = job.get("title", "")
            description = job.get("description", "")
            job_text = f"{title} {description}".lower() if description else title.lower()
            job_texts.append(self._preprocess_text(job_text))
            job_skills_list.append(self.extract_skills(job_text))
            
        # Pre-extract job experience requirements
        job_exp_list = [self.extract_experience_years(t, is_resume=False) for t in job_texts]
            
        # Calculate TF-IDF for all simultaneously (Matrix operation)
        tfidf_scores = [0] * len(jobs)
        try:
            if len(self.resume_text_processed.split()) >= 5:
                vectorizer = TfidfVectorizer(
                    analyzer='char',
                    ngram_range=(2, 3),
                    lowercase=True,
                    stop_words='english'
                )
                corpus = [self.resume_text_processed] + job_texts
                tfidf_matrix = vectorizer.fit_transform(corpus)
                similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
                tfidf_scores = similarities[0] * 100
        except Exception:
            pass

        # Compile final scores
        for i, job in enumerate(jobs):
            job_id = job.get("job_id")
            job_skills = job_skills_list[i]
            
            matching_skills = list(set(self.resume_skills) & set(job_skills))
            missing_skills = list(set(job_skills) - set(self.resume_skills))
            
            if job_skills:
                skill_score = (len(matching_skills) / len(job_skills)) * 40
            else:
                skill_score = 20
                
            final_score = min(100, (float(tfidf_scores[i]) * 0.5) + skill_score)
            
            # Apply experience penalty if job asks for more experience than resume has
            job_exp = job_exp_list[i]
            exp_penalty = 0
            if job_exp > 0 and self.resume_experience_years < job_exp:
                gap = job_exp - self.resume_experience_years
                # penalize up to 20 points
                exp_penalty = min(20, (gap / job_exp) * 20)
                final_score = max(0, final_score - exp_penalty)
            
            explanation = self._generate_explanation(
                final_score + exp_penalty, # base explanation on unpenalized score
                len(matching_skills),
                len(missing_skills),
                len(job_skills)
            )
            
            if exp_penalty > 0:
                explanation += f" Note: Job asks for {job_exp} years experience, but resume shows ~{self.resume_experience_years} years (internships excluded)."
            
            # Detailed feedback
            pros = []
            cons = []
            if matching_skills:
                pros.append(f"You have {len(matching_skills)} required skills ({', '.join(matching_skills[:5])}{'...' if len(matching_skills)>5 else ''}).")
            if missing_skills:
                cons.append(f"You are missing {len(missing_skills)} recommended skills ({', '.join(missing_skills[:5])}{'...' if len(missing_skills)>5 else ''}).")
            if job_exp > 0:
                if self.resume_experience_years >= job_exp:
                    pros.append(f"You meet the experience requirement (Requires {job_exp} years, you have ~{self.resume_experience_years} years).")
                else:
                    cons.append(f"You may fall short on experience (Requires {job_exp} years, you have ~{self.resume_experience_years} years).")
            else:
                pros.append(f"Your experience (~{self.resume_experience_years} years) looks sufficient as no strict minimum was found.")

            results.append({
                "job_id": job_id,
                "score": round(final_score, 1),
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "explanation": explanation,
                "pros": pros,
                "cons": cons,
                "job_experience_required": job_exp,
                "candidate_experience": self.resume_experience_years
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
