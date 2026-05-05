"""
MongoDB Atlas setup — mirrors the SQL schema defined in create_db.py and DatabaseStructure.md.

Collections created:
  jobs              ← mirrors the "jobs" table
  salaries          ← mirrors the "salaries" table  (embedded or standalone)
  benefits          ← mirrors the "benefits" table  (embedded or standalone)
  companies         ← mirrors the "companies" table
  employee_counts   ← mirrors the "employee_counts" table
  skills            ← mirrors the "skills" table
  job_skills        ← mirrors the "job_skills" join table
  industries        ← mirrors the "industries" table
  job_industries    ← mirrors the "job_industries" join table
  company_specialities ← mirrors the "company_specialities" table
  company_industries   ← mirrors the "company_industries" table

Unique indexes are applied to match the PRIMARY KEY constraints in the SQL schema.
"""

import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv

load_dotenv()

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a cached MongoClient instance."""
    global _client
    if _client is None:
        uri = os.environ["MONGODB_URI"]
        _client = MongoClient(uri)
    return _client


def get_db():
    """Return the configured database object."""
    db_name = os.getenv("MONGODB_DB_NAME", "linkedin_jobs")
    return get_client()[db_name]


# ---------------------------------------------------------------------------
# Collection + index setup
# ---------------------------------------------------------------------------

def _ensure_collection(db, name: str):
    """Create the collection if it doesn't exist (no-op if already present)."""
    try:
        db.create_collection(name)
    except CollectionInvalid:
        pass  # already exists


def setup_collections(db=None):
    """
    Ensure all collections exist and carry the correct unique indexes.
    Safe to call multiple times (idempotent).
    """
    if db is None:
        db = get_db()

    # ── jobs ──────────────────────────────────────────────────────────────
    _ensure_collection(db, "jobs")
    db["jobs"].create_index(
        [("job_id", ASCENDING)],
        unique=True,
        name="job_id_unique",
    )

    # ── salaries ──────────────────────────────────────────────────────────
    # salary_id is NOT provided by LinkedIn's API — MongoDB's _id is the PK.
    # We only need a fast lookup index by job_id (not unique: one job → many salaries).
    _ensure_collection(db, "salaries")
    # Drop the old broken unique index on salary_id if it still exists on Atlas
    try:
        db["salaries"].drop_index("salary_id_unique")
    except Exception:
        pass  # index doesn't exist — nothing to do
    db["salaries"].create_index(
        [("job_id", ASCENDING)],
        name="salary_job_id",
    )

    # ── benefits ──────────────────────────────────────────────────────────
    # PRIMARY KEY (job_id, type)
    _ensure_collection(db, "benefits")
    db["benefits"].create_index(
        [("job_id", ASCENDING), ("type", ASCENDING)],
        unique=True,
        name="benefit_job_type_unique",
    )

    # ── companies ─────────────────────────────────────────────────────────
    _ensure_collection(db, "companies")
    db["companies"].create_index(
        [("company_id", ASCENDING)],
        unique=True,
        name="company_id_unique",
    )

    # ── employee_counts ───────────────────────────────────────────────────
    # PRIMARY KEY (employee_count, company_id)
    _ensure_collection(db, "employee_counts")
    db["employee_counts"].create_index(
        [("company_id", ASCENDING), ("employee_count", ASCENDING)],
        unique=True,
        name="employee_count_pk",
    )

    # ── skills ────────────────────────────────────────────────────────────
    _ensure_collection(db, "skills")
    db["skills"].create_index(
        [("skill_abr", ASCENDING)],
        unique=True,
        name="skill_abr_unique",
    )

    # ── job_skills ────────────────────────────────────────────────────────
    # PRIMARY KEY (job_id, skill_abr)
    _ensure_collection(db, "job_skills")
    db["job_skills"].create_index(
        [("job_id", ASCENDING), ("skill_abr", ASCENDING)],
        unique=True,
        name="job_skill_pk",
    )

    # ── industries ────────────────────────────────────────────────────────
    _ensure_collection(db, "industries")
    db["industries"].create_index(
        [("industry_id", ASCENDING)],
        unique=True,
        name="industry_id_unique",
    )

    # ── job_industries ────────────────────────────────────────────────────
    # PRIMARY KEY (job_id, industry_id)
    _ensure_collection(db, "job_industries")
    db["job_industries"].create_index(
        [("job_id", ASCENDING), ("industry_id", ASCENDING)],
        unique=True,
        name="job_industry_pk",
    )

    # ── company_specialities ──────────────────────────────────────────────
    # PRIMARY KEY (company_id, speciality)
    _ensure_collection(db, "company_specialities")
    db["company_specialities"].create_index(
        [("company_id", ASCENDING), ("speciality", ASCENDING)],
        unique=True,
        name="company_speciality_pk",
    )

    # ── company_industries ────────────────────────────────────────────────
    # PRIMARY KEY (company_id, industry)
    _ensure_collection(db, "company_industries")
    db["company_industries"].create_index(
        [("company_id", ASCENDING), ("industry", ASCENDING)],
        unique=True,
        name="company_industry_pk",
    )

    print("[MongoDB] All collections and indexes are ready.")
    return True
