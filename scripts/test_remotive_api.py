import json
from server.connectors.remotive import fetch_remotive_jobs

if __name__ == "__main__":
    query = "data"   # essaie aussi "python", "sql"
    limit = 10

    jobs = fetch_remotive_jobs(query=query, limit=limit)

    print(f"[OK] Remotive returned {len(jobs)} jobs for query='{query}'")
    if jobs:
        sample = jobs[0]
        print("\n--- Sample job ---")
        print("title:", sample.get("title"))
        print("company:", sample.get("company_name"))
        print("location:", sample.get("candidate_required_location"))
        print("url:", sample.get("url"))

    # Option: save to file
    with open("data/cache/remotive_sample.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    print("\nSaved -> data/cache/remotive_sample.json")