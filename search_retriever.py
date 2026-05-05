from scripts.mongodb import setup_collections, get_db
from scripts.mongodb_scripts import insert_job_postings_mongo
from scripts.fetch import JobSearchRetriever
import time
from collections import deque

sleep_times  = deque(maxlen=5)
first        = True
sleep_factor = 3

# ── Setup MongoDB collections / indexes ──────────────────────────────────────
db = get_db()
setup_collections(db)

# ── Start scraper loop ────────────────────────────────────────────────────────
job_searcher = JobSearchRetriever()

while True:
    all_results = job_searcher.get_jobs()

    # Find job_ids already in the database
    existing_ids = {
        doc["job_id"]
        for doc in db["jobs"].find(
            {"job_id": {"$in": list(all_results.keys())}},
            {"job_id": 1, "_id": 0},
        )
    }

    new_results = {
        job_id: job_info
        for job_id, job_info in all_results.items()
        if job_id not in existing_ids
    }

    insert_job_postings_mongo(new_results)

    total_non_sponsored = len([x for x in all_results.values() if not x["sponsored"]])
    new_non_sponsored   = len([x for x in new_results.values() if not x["sponsored"]])
    print(
        f"{len(new_results)}/{len(all_results)} NEW RESULTS | "
        f"{new_non_sponsored}/{total_non_sponsored} NEW NON-PROMOTED RESULTS"
    )

    if not first:
        seconds_per_job = sleep_factor / max(len(new_results), 1)
        sleep_factor    = min(seconds_per_job * total_non_sponsored * 0.75, 200)
    first = False

    print(f"Sleeping For {min(200, sleep_factor):.1f} Seconds...")
    time.sleep(min(200, sleep_factor))
    print("Resuming...")
