# LinkedIn Job Scraper with API & Dashboard

Complete setup guide for the new API and UI system.

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- LinkedIn cookies file (`linkedin_cookies.json`)
- Login credentials in `logins.csv`

### 2. Setup

```bash
# Copy environment template to .env
cp .env.template .env

# Edit .env with your MongoDB credentials
nano .env

# Generate LinkedIn cookies
python generate_cookies.sh

# Build and start services
docker-compose up -d
```

### 3. Access the Dashboard

Open your browser and navigate to:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

---

## 📊 Components

### Services

#### API Service (Port 8000)
- FastAPI server with REST API
- Serves the web dashboard
- Handles all business logic
- Documentation at `/docs` (Swagger UI)

#### MongoDB (Port 27017)
- Stores all job data
- Resume information
- Bookmarks and relevance scores
- Scraper logs

#### Search Scraper
- Continuously collects job IDs
- Updates MongoDB with latest jobs
- Runs automatically in background

#### Details Scraper
- Fetches full job information
- Populates missing fields
- Runs after search scraper

---

## 🎨 Dashboard Features

### 1. Jobs Tab
- Browse all scraped jobs
- Filter by location, work type, salary
- Search by keywords
- View job details
- Bookmark jobs for later
- See relevance scores (based on resume)

### 2. Resume Tab
- Upload resume (TXT, PDF, DOCX)
- View extracted skills
- Analyze relevance against all jobs
- See matching percentage

### 3. Bookmarks Tab
- View all saved jobs
- Add notes to bookmarks
- Quick access to favorite jobs
- Remove bookmarks

### 4. Scraper Tab
- Monitor scraper status
- View job statistics
- Start/stop scraping manually
- Toggle full details fetching
- View recent logs

---

## 🔌 API Endpoints

### Jobs
- `GET /api/jobs` - List jobs with filters
- `GET /api/jobs/{job_id}` - Get job details
- `POST /api/jobs/bookmark/{job_id}` - Bookmark a job
- `DELETE /api/jobs/bookmark/{job_id}` - Remove bookmark
- `GET /api/jobs/bookmarks/all` - Get all bookmarks
- `GET /api/jobs/relevance/scores` - Get jobs sorted by relevance
- `POST /api/jobs/calculate-relevance` - Calculate scores for jobs

### Resume
- `POST /api/resume/upload` - Upload resume file
- `GET /api/resume/{resume_id}` - Get resume details
- `GET /api/resume/latest` - Get most recent resume
- `POST /api/resume/analyze-relevance` - Analyze all jobs against resume
- `GET /api/resume/text/{resume_id}` - Get full resume text

### Scraper
- `GET /api/scraper/status` - Get scraper status & stats
- `POST /api/scraper/trigger` - Start scraper
- `POST /api/scraper/stop` - Stop scraper
- `GET /api/scraper/logs` - Get recent logs

### Health
- `GET /api/health` - Health check

---

## 💾 Database Structure

### Collections

#### jobs
Original LinkedIn jobs data with additional fields:
- job_id, company_id, title, description
- Salary info, location, work type
- Experience level, remote allowed
- Skills required, posting URL
- Status: scraped (true/false)

#### resumes
Uploaded resume information:
- resume_id, filename, content
- extracted_skills (array)
- uploaded_at (timestamp)

#### bookmarks
Saved jobs:
- job_id, notes, created_at

#### relevance_scores
Resume-to-job matching scores:
- resume_id, job_id, score
- matching_skills, missing_skills
- explanation, skill_match_percentage

#### scraper_logs
Scraper events and status:
- event_type, timestamp, details

---

## 📋 Resume Matching Algorithm

The system uses a hybrid approach:

1. **Skill Extraction**
   - Identifies technical skills from resume
   - Matches against common skill database
   - Compares with job requirements

2. **TF-IDF Similarity**
   - Analyzes resume text
   - Compares with job description
   - Generates similarity score

3. **Combined Scoring**
   - Skill match (40% weight)
   - Text similarity (60% weight)
   - Final score: 0-100%

### Score Interpretation
- **80-100%**: Excellent match - You have most/all required skills
- **60-79%**: Good match - You meet most requirements
- **40-59%**: Moderate match - Some required skills missing
- **0-39%**: Low match - Consider developing missing skills

---

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f search
docker-compose logs -f details

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Access MongoDB shell
docker exec -it linkedin_scraper_db mongosh -u scraper -p password --authenticationDatabase admin

# View API documentation
# Open http://localhost:8000/docs
```

---

## 📁 File Structure

```
├── api/
│   ├── main.py                 # FastAPI app
│   ├── models.py               # Pydantic models
│   ├── database.py             # MongoDB operations
│   ├── routes/
│   │   ├── jobs.py            # Job endpoints
│   │   ├── resume.py          # Resume endpoints
│   │   └── scraper.py         # Scraper endpoints
│   └── services/
│       └── resume_matcher.py  # Resume analysis
├── frontend/
│   ├── index.html             # Main dashboard
│   ├── styles.css             # Styling
│   └── app.js                 # JavaScript logic
├── docker-compose.yml         # Docker services
├── Dockerfile                 # Container image
├── requirements.txt           # Python dependencies
└── .env.template              # Environment variables
```

---

## 🔧 Configuration

### Environment Variables

Edit `.env` to customize:

```env
# Database
MONGO_USER=scraper
MONGO_PASSWORD=your_password
MONGODB_DB_NAME=linkedin_jobs

# API
API_PORT=8000
PYTHONUNBUFFERED=1

# Scraper
HEADLESS=true
SEARCH_KEYWORDS=Python,JavaScript,DevOps
```

### Search Keywords

Modify in `search_retriever.py`:
```python
SEARCH_KEYWORDS = [
    "Python Engineer",
    "Full Stack Developer",
    "Backend Developer"
]
```

---

## 📊 Monitoring

### View Dashboard Logs
```bash
docker-compose logs -f api
```

### Monitor Database
```bash
docker exec linkedin_scraper_db mongosh \
  -u scraper -p password \
  --authenticationDatabase admin \
  --eval "db.jobs.countDocuments()"
```

### Check Scraper Status
Navigate to Scraper tab in dashboard or:
```bash
curl http://localhost:8000/api/scraper/status
```

---

## 🚨 Troubleshooting

### API won't start
```bash
# Check logs
docker-compose logs api

# Rebuild
docker-compose build --no-cache api
docker-compose up api
```

### MongoDB connection error
```bash
# Check MongoDB is running
docker-compose logs mongodb

# Verify credentials in .env
```

### Resume upload fails
- Ensure file is TXT, PDF, or DOCX
- Check file size (should be < 10MB)
- Try again or use different format

### No relevance scores showing
- Upload a resume first in Resume tab
- Click "Analyze & Calculate Relevance Scores"
- Wait for analysis to complete
- Switch to Jobs tab to see scored jobs

---

## 📚 Additional Resources

### API Documentation
Interactive docs available at: http://localhost:8000/docs

### MongoDB
- [MongoDB Docs](https://docs.mongodb.com)
- Connect with: `mongodb://scraper:password@localhost:27017`

### FastAPI
- [FastAPI Docs](https://fastapi.tiangolo.com)
- Built on Uvicorn ASGI server

---

## 📝 License

Part of the agentic-linkedin-scraper project

---

## ❓ FAQ

**Q: How do I change MongoDB credentials?**
A: Edit `.env` and restart services: `docker-compose restart`

**Q: Can I run the scraper without Docker?**
A: Yes, but you need MongoDB running locally

**Q: How often are jobs updated?**
A: Continuously - see `search_retriever.py` and `details_retriever.py` for intervals

**Q: Can I export jobs to CSV?**
A: Yes, use the original `to_csv.py` script

**Q: How are relevance scores calculated?**
A: See README.md "Resume Matching Algorithm" section

---

For more help, check the API documentation at `/docs` or check logs with `docker-compose logs`
