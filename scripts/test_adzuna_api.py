import json
from server.connectors.adzuna import fetch_adzuna_jobs

if __name__ == "__main__":
    query = "data analyst"
    location = "Paris"
    limit = 10

    jobs = fetch_adzuna_jobs(query=query, location=location, limit=limit)

    print(f"[OK] Adzuna returned {len(jobs)} jobs for query='{query}' location='{location}'")
    if jobs:
        j = jobs[0]
        print("\n--- Sample job ---")
        print("title:", j.get("title"))
        company = (j.get("company") or {}).get("display_name")
        print("company:", company)
        loc = (j.get("location") or {}).get("display_name")
        print("location:", loc)
        print("url:", j.get("redirect_url"))

    with open("data/cache/adzuna_sample.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    print("\nSaved -> data/cache/adzuna_sample.json")