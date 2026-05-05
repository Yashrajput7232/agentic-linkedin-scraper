from scripts.mongodb import setup_collections, get_db
from scripts.mongodb_scripts import insert_data_mongo
from scripts.fetch import JobDetailRetriever
from scripts.helpers import clean_job_postings
import time
import random

SLEEP_TIME  = 60
MAX_UPDATES = 25

# ── Setup MongoDB collections / indexes ──────────────────────────────────────
db = get_db()
setup_collections(db)

# ── Start scraper loop ────────────────────────────────────────────────────────
job_detail_retriever = JobDetailRetriever()

while True:
    # Find all jobs that haven't been fully scraped yet (scraped == 0)
    pending = [
        doc["job_id"]
        for doc in db["jobs"].find({"scraped": 0}, {"job_id": 1, "_id": 0})
    ]

    sample = random.sample(pending, min(MAX_UPDATES, len(pending)))

    details = job_detail_retriever.get_job_details(sample)
    details = clean_job_postings(details)
    insert_data_mongo(details)

    print(f"UPDATED {len(details)} VALUES IN DB")
    print(f"Sleeping For {SLEEP_TIME} Seconds...")
    time.sleep(SLEEP_TIME)
    print("Resuming...")
