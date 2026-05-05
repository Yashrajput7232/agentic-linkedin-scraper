"""
MongoDB equivalents of the SQLite operations in database_scripts.py.

Function mapping:
  insert_job_postings  → insert_job_postings_mongo
  insert_data          → insert_data_mongo
"""

import time
from pymongo import UpdateOne, InsertOne
from pymongo.errors import BulkWriteError

from scripts.mongodb import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert(collection, filter_doc: dict, update_doc: dict):
    """Upsert a single document — mirrors INSERT OR REPLACE."""
    collection.update_one(filter_doc, {"$set": update_doc}, upsert=True)


def _insert_if_missing(collection, filter_doc: dict, document: dict):
    """Insert only when the document doesn't exist — mirrors INSERT OR IGNORE."""
    collection.update_one(filter_doc, {"$setOnInsert": document}, upsert=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def insert_job_postings_mongo(job_ids: dict):
    """
    Mirrors:  INSERT OR IGNORE INTO jobs (job_id, title, sponsored) VALUES (?, ?, ?)

    job_ids: {job_id: {'title': ..., 'sponsored': ...}, ...}
    """
    db = get_db()
    jobs_col = db["jobs"]

    ops = []
    for job_id, info in job_ids.items():
        doc = {
            "job_id": job_id,
            "title": info.get("title"),
            "sponsored": info.get("sponsored", False),
            "scraped": 0,          # mirrors DEFAULT 0
        }
        ops.append(
            UpdateOne(
                {"job_id": job_id},
                {"$setOnInsert": doc},
                upsert=True,
            )
        )
    if ops:
        try:
            jobs_col.bulk_write(ops, ordered=False)
        except BulkWriteError:
            pass  # duplicate-key errors from race conditions are fine
    return True


def insert_data_mongo(data: dict):
    """
    Mirrors the insert_data() function in database_scripts.py.

    data: {job_id: {'jobs': {...}, 'companies': {...}, 'salaries': {...},
                    'benefits': {...}, 'industries': {...}, 'skills': {...},
                    'employee_counts': {...}, 'company_industries': {...},
                    'company_specialities': {...}}}
    """
    db = get_db()
    jobs_col             = db["jobs"]
    benefits_col         = db["benefits"]
    industries_col       = db["industries"]
    job_industries_col   = db["job_industries"]
    skills_col           = db["skills"]
    job_skills_col       = db["job_skills"]
    salaries_col         = db["salaries"]
    companies_col        = db["companies"]
    employee_counts_col  = db["employee_counts"]
    company_industries_col     = db["company_industries"]
    company_specialities_col   = db["company_specialities"]

    for job_id, job_info in data.items():

        # ── error case ────────────────────────────────────────────────────
        if "error" in job_info:
            jobs_col.update_one({"job_id": job_id}, {"$set": {"scraped": -1}})
            continue

        company_id = job_info["jobs"].get("company_id")

        # ── jobs ─────────────────────────────────────────────────────────
        if job_info.get("jobs"):
            update_fields = dict(job_info["jobs"])
            update_fields["scraped"] = round(time.time())   # mirrors "scraped = ?"
            jobs_col.update_one(
                {"job_id": job_id},
                {"$set": update_fields},
                upsert=True,
            )

        # ── benefits ─────────────────────────────────────────────────────
        if job_info.get("benefits"):
            benefits = job_info["benefits"]

            for benefit in benefits.get("listed_benefits", []):
                _insert_if_missing(
                    benefits_col,
                    {"job_id": job_id, "type": benefit},
                    {"job_id": job_id, "inferred": 0, "type": benefit},
                )

            for benefit in benefits.get("inferred_benefits", []):
                _insert_if_missing(
                    benefits_col,
                    {"job_id": job_id, "type": benefit},
                    {"job_id": job_id, "inferred": 1, "type": benefit},
                )

        # ── industries ───────────────────────────────────────────────────
        if job_info.get("industries") and "industry_ids" in job_info["industries"]:
            ind_data = job_info["industries"]
            ind_ids   = ind_data["industry_ids"]
            ind_names = ind_data.get("industry_names", [])

            for i, industry_id in enumerate(ind_ids):
                industry_name = ind_names[i] if i < len(ind_names) else None

                # Upsert industry (keep existing name if already present)
                industries_col.update_one(
                    {"industry_id": industry_id},
                    {
                        "$setOnInsert": {"industry_id": industry_id},
                        "$set": {"industry_name": industry_name} if industry_name else {},
                    },
                    upsert=True,
                )
                _insert_if_missing(
                    job_industries_col,
                    {"job_id": job_id, "industry_id": industry_id},
                    {"job_id": job_id, "industry_id": industry_id},
                )

        # ── skills ───────────────────────────────────────────────────────
        if job_info.get("skills") and "skill_abrs" in job_info["skills"]:
            sk_data   = job_info["skills"]
            skill_abrs = sk_data["skill_abrs"]
            skill_names = sk_data.get("skill_name", [])

            for i, skill_abr in enumerate(skill_abrs):
                skill_name = skill_names[i] if i < len(skill_names) else None

                skills_col.update_one(
                    {"skill_abr": skill_abr},
                    {
                        "$setOnInsert": {"skill_abr": skill_abr},
                        "$set": {"skill_name": skill_name} if skill_name else {},
                    },
                    upsert=True,
                )
                _insert_if_missing(
                    job_skills_col,
                    {"job_id": job_id, "skill_abr": skill_abr},
                    {"job_id": job_id, "skill_abr": skill_abr},
                )

        # ── salaries ─────────────────────────────────────────────────────
        if job_info.get("salaries"):
            for compensation_type, values in job_info["salaries"].items():
                for compensation in values:
                    doc = {
                        "job_id":            job_id,
                        "max_salary":        compensation.get("maxSalary"),
                        "med_salary":        compensation.get("medianSalary"),
                        "min_salary":        compensation.get("minSalary"),
                        "pay_period":        compensation.get("payPeriod"),
                        "currency":          compensation.get("currencyCode"),
                        "compensation_type": compensation.get("compensationType"),
                    }
                    salaries_col.insert_one(doc)

        # ── companies ────────────────────────────────────────────────────
        if job_info.get("companies") and company_id is not None:
            company_doc = dict(job_info["companies"])
            company_doc["company_id"] = company_id
            _upsert(companies_col, {"company_id": company_id}, company_doc)

        # ── employee_counts ──────────────────────────────────────────────
        if job_info.get("employee_counts") and company_id is not None:
            ec = job_info["employee_counts"]
            ec_doc = {
                "company_id":     company_id,
                "employee_count": ec.get("employee_count"),
                "follower_count": ec.get("follower_count"),
                "time_recorded":  round(time.time()),
            }
            _insert_if_missing(
                employee_counts_col,
                {"company_id": company_id, "employee_count": ec_doc["employee_count"]},
                ec_doc,
            )

        # ── company_industries ───────────────────────────────────────────
        if job_info.get("company_industries") and company_id is not None:
            for industry in job_info["company_industries"].get("industries", []):
                _insert_if_missing(
                    company_industries_col,
                    {"company_id": company_id, "industry": industry},
                    {"company_id": company_id, "industry": industry},
                )

        # ── company_specialities ─────────────────────────────────────────
        if job_info.get("company_specialities") and company_id is not None:
            for speciality in job_info["company_specialities"].get("specialities", []):
                _insert_if_missing(
                    company_specialities_col,
                    {"company_id": company_id, "speciality": speciality},
                    {"company_id": company_id, "speciality": speciality},
                )

    return True
