"""
match_jobs.py — Score stored jobs against your resume skills and print ranked matches.

Usage:
    python match_jobs.py

Configure your skills in .env:
    RESUME_SKILLS=Python,Machine Learning,SQL,Data Engineering,Spark,Airflow,AWS

Only jobs with scraped > 0 (full details fetched) are scored.
"""

import os
from dotenv import load_dotenv
from scripts.mongodb import get_db

load_dotenv()

# ── Load your skills from .env ────────────────────────────────────────────────
raw_skills = os.getenv("RESUME_SKILLS", "")
if not raw_skills:
    print("⚠️  No RESUME_SKILLS found in .env")
    print("    Add a line like:")
    print("    RESUME_SKILLS=Python,Machine Learning,SQL,Data Engineering,AWS")
    exit(1)

resume_skills = [s.strip().lower() for s in raw_skills.split(",") if s.strip()]
print(f"Your skills ({len(resume_skills)}): {', '.join(resume_skills)}\n")

# ── Fetch fully-scraped jobs from MongoDB ─────────────────────────────────────
db = get_db()
jobs = list(db["jobs"].find(
    {"scraped": {"$gt": 0}},
    {"_id": 0, "job_id": 1, "title": 1, "description": 1,
     "skills_desc": 1, "location": 1, "formatted_work_type": 1,
     "formatted_experience_level": 1, "job_posting_url": 1}
))

if not jobs:
    print("No fully-scraped jobs yet. Run details_retriever.py first.")
    exit(0)

print(f"Scoring {len(jobs)} jobs...\n")

# ── Score each job ────────────────────────────────────────────────────────────
def score_job(job: dict, skills: list[str]) -> tuple[int, list[str]]:
    """Count how many resume skills appear in the job text. Return (score, matched_skills)."""
    text = " ".join(filter(None, [
        job.get("title", ""),
        job.get("description", ""),
        job.get("skills_desc", ""),
    ])).lower()

    matched = [skill for skill in skills if skill in text]
    return len(matched), matched


scored = []
for job in jobs:
    score, matched = score_job(job, resume_skills)
    if score > 0:
        scored.append({**job, "_score": score, "_matched": matched})

scored.sort(key=lambda j: j["_score"], reverse=True)

# ── Print results ─────────────────────────────────────────────────────────────
print(f"{'Rank':<5} {'Score':<7} {'Title':<50} {'Location':<25} Matched Skills")
print("─" * 130)

for i, job in enumerate(scored[:30], 1):     # top 30
    title    = (job.get("title") or "N/A")[:48]
    location = (job.get("location") or "N/A")[:23]
    matched  = ", ".join(job["_matched"])
    url      = job.get("job_posting_url", "")
    print(f"{i:<5} {job['_score']:<7} {title:<50} {location:<25} {matched}")
    if url:
        print(f"      🔗 {url}")

print(f"\n{len(scored)} relevant jobs found out of {len(jobs)} scraped.")

# ── Save results to a file ────────────────────────────────────────────────────
import json
out_path = "matched_jobs.json"
with open(out_path, "w") as f:
    json.dump(
        [{k: v for k, v in j.items() if not k.startswith("_")} | {"score": j["_score"], "matched_skills": j["_matched"]}
         for j in scored],
        f, indent=2
    )
print(f"\nFull results saved to: {out_path}")
