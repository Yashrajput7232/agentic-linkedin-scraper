# LinkedIn Job Scraper - API and Dashboard

## 🎯 Overview

Complete system with:
- **REST API** built with FastAPI
- **Interactive Dashboard** with resume matching
- **Resume Analyzer** with skill extraction
- **Job Scraper** with relevance scoring
- **Docker Setup** for easy deployment

Everything runs in Docker containers for easy setup and management.

---

## 🚀 Quick Start (Docker)

### 1. Minimal Setup
```bash
bash quickstart.sh
```

This will:
1. Verify Docker is installed
2. Generate LinkedIn cookies (if needed)
3. Build Docker images
4. Start all services
5. Open the dashboard at `http://localhost:8000`

### 2. Manual Setup
```bash
# Copy environment file
cp .env.template .env

# Generate LinkedIn cookies
python generate_cookies.sh

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
```

### 3. Local Setup (without Docker)
```bash
bash setup_local.sh

# Activate environment
source venv/bin/activate

# Start API (requires MongoDB running)
uvicorn api.main:app --reload
```

---

## 📊 Features

### 🎨 Dashboard UI
- **Jobs Tab**: Browse jobs, filter, search, bookmark, view details
- **Resume Tab**: Upload resume, extract skills, analyze relevance
- **Bookmarks Tab**: Save favorite jobs with notes
- **Scraper Tab**: Monitor scraping progress, control scraper

### 🧠 Resume Matching
- Upload Resume (TXT, PDF, DOCX)
- Automatic skill extraction
- TF-IDF similarity matching
- Relevance scoring (0-100%)
- Identify matching & missing skills

### 🔍 Job Management
- Real-time job scraping
- Advanced filtering (location, type, salary)
- Full-text search
- Bookmark/save jobs
- View complete details

### ⚙️ Scraper Control
- Start/stop scraper from UI
- Monitor job statistics
- View event logs
- Optional full details fetching

---

## 🔌 API Endpoints

Full API documentation available at: **http://localhost:8000/docs**

### Key Endpoints

```
Jobs:
  GET  /api/jobs              # List jobs (with filters)
  GET  /api/jobs/{job_id}     # Get job details
  POST /api/jobs/bookmark/{job_id}  # Bookmark job

Resume:
  POST /api/resume/upload          # Upload resume
  GET  /api/resume/latest          # Get latest resume
  POST /api/resume/analyze-relevance  # Analyze all jobs

Scraper:
  GET  /api/scraper/status    # Get scraper status
  POST /api/scraper/trigger   # Start scraper
  POST /api/scraper/stop      # Stop scraper
```

---

## 📁 Project Structure

```
agentic-linkedin-scraper/
├── api/                      # FastAPI backend
│   ├── main.py              # Main application
│   ├── models.py            # Data models
│   ├── database.py          # MongoDB layer
│   ├── routes/              # API endpoints
│   └── services/            # Business logic
├── frontend/                # Dashboard UI
│   ├── index.html          # Main page
│   ├── styles.css          # Styling
│   └── app.js              # JavaScript
├── scripts/                 # Original scraping scripts
├── dockerfile               # Container image
├── docker-compose.yml      # Service orchestration
├── requirements.txt        # Python dependencies
└── SETUP_GUIDE.md         # Complete documentation
```

---

## 🐳 Docker Services

### Running Services
- **mongodb**: Document database (port 27017)
- **api**: FastAPI dashboard & API (port 8000)
- **search**: Job ID scraper (background)
- **details**: Job details fetcher (background)

### Docker Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f <service>

# Stop all
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Run single service
docker-compose up -d api
```

---

## 📖 Usage Guide

### 1. Upload Resume
- Click "Resume" tab
- Select your resume file (TXT, PDF, or DOCX)
- System extracts skills automatically

### 2. Analyze & Score Jobs
- Click "Analyze & Calculate Relevance Scores"
- System scores all jobs against your resume
- Generates match percentages and skill analysis

### 3. Browse Jobs
- Click "Jobs" tab
- Jobs sorted by relevance score
- Green badge = excellent match (80%+)
- Orange badge = good match (60-79%)

### 4. Bookmark Jobs
- Click star icon to save job
- Add notes if desired
- Access later in "Bookmarks" tab

### 5. Control Scraper
- Go to "Scraper" tab
- Click "Start Scraper"
- Monitor progress in real-time
- View job statistics

---

## 💾 Database

### MongoDB Collections

#### jobs
LinkedIn job postings with metadata
```json
{
  "job_id": "123456",
  "title": "Python Engineer",
  "company_id": "google",
  "location": "San Francisco, CA",
  "description": "...",
  "skills_desc": "Python, Django, REST...",
  "relevance_score": 85.5,
  "is_bookmarked": false
}
```

#### resumes
Uploaded resumes with extracted data
```json
{
  "resume_id": "resume_abc123",
  "filename": "resume.pdf",
  "content": "John Doe...",
  "extracted_skills": ["Python", "JavaScript", "React"],
  "uploaded_at": "2024-01-15T10:30:00Z"
}
```

#### relevance_scores
Resume-to-job matching results
```json
{
  "resume_id": "resume_abc123",
  "job_id": "123456",
  "score": 85.5,
  "matching_skills": ["Python", "Django"],
  "missing_skills": ["Kubernetes"]
}
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```env
MONGO_USER=scraper
MONGO_PASSWORD=password
MONGODB_DB_NAME=linkedin_jobs
MONGODB_URL=mongodb://scraper:password@mongodb:27017/linkedin_jobs
API_PORT=8000
HEADLESS=true
```

### Search Keywords
Edit in `search_retriever.py`:
```python
SEARCH_KEYWORDS = [
    "Python Engineer",
    "Full Stack Developer"
]
```

---

## 🧠 Resume Matching Algorithm

### How It Works
1. **Skill Extraction** (50%)
   - Identifies technical skills from resume
   - Matches against job requirements
   - Generates skill overlap percentage

2. **Text Similarity** (50%)
   - TF-IDF analysis of resume vs job description
   - Cosine similarity matching
   - Measures overall relevance

### Score Ranges
- **80-100%**: Excellent match - Perfect fit
- **60-79%**: Good match - Well qualified
- **40-59%**: Fair match - Some gaps
- **0-39%**: Low match - Consider development

---

## 🚨 Troubleshooting

### Services Won't Start
```bash
docker-compose logs
docker-compose build --no-cache
docker-compose up -d
```

### MongoDB Connection Error
```bash
docker-compose logs mongodb
# Check .env credentials match docker-compose.yml
```

### Resume Upload Fails
- Ensure format is TXT, PDF, or DOCX
- Keep file under 10MB
- Try PDF if other formats fail

### No Relevance Scores Showing
1. Upload resume first
2. Click "Analyze & Calculate Relevance Scores"
3. Wait for analysis (takes 10-30 seconds)
4. Switch to Jobs tab

---

## 📚 Documentation

- **Setup Guide**: See [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **API Docs**: Visit http://localhost:8000/docs
- **Original Project**: See [README.md](README.md)

---

## 🔧 Development

### Running Tests
```bash
# Check API health
curl http://localhost:8000/api/health

# Create sample job (for testing)
curl -X GET http://localhost:8000/api/jobs
```

### Building for Production
```bash
docker build -t linkedin-scraper:latest .
docker run -p 8000:8000 linkedin-scraper:latest
```

---

## 📞 Support

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change port in docker-compose.yml |
| MongoDB auth fails | Check .env credentials |
| Resume not uploading | Ensure PDF/TXT/DOCX format |
| No jobs appearing | Check scraper logs, trigger scra per manually |

### Getting Help
1. Check logs: `docker-compose logs`
2. Review [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Check API docs: http://localhost:8000/docs

---

## 📝 License

Part of agentic-linkedin-scraper project

---

## ✨ Features Added

This version adds to the original scraper:
- ✅ Full REST API with FastAPI
- ✅ Interactive web dashboard
- ✅ Resume skill extraction  
- ✅ Resume-to-job relevance scoring
- ✅ Job bookmarking & notes
- ✅ Job filtering & search
- ✅ Scraper status monitoring
- ✅ Docker deployment ready
- ✅ MongoDB integration

---

**Happy job hunting! 🚀**
