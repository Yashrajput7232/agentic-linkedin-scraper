from scripts.mongodb import get_db

db = get_db()

total   = db["jobs"].count_documents({})
scraped = db["jobs"].count_documents({"scraped": {"$gt": 0}})
pending = db["jobs"].count_documents({"scraped": 0})
errors  = db["jobs"].count_documents({"scraped": -1})

print(f"Database  : {db.name}")
print(f"─────────────────────────────")
print(f"Total jobs stored : {total}")
print(f"Fully scraped     : {scraped}")
print(f"Pending details   : {pending}")
print(f"Errors            : {errors}")
print()
print("Sample records (latest 5):")
for j in db["jobs"].find({}, {"_id": 0, "job_id": 1, "title": 1, "location": 1, "scraped": 1}).limit(5):
    print(" ", j)
