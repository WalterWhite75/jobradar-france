from server.utils.http import get_json

REMOTIVE_API = "https://remotive.com/api/remote-jobs"

def fetch_remotive_jobs(query: str, limit: int = 10) -> list[dict]:
    """
    Remotive API is open. It returns a JSON with key 'jobs' (list).
    """
    params = {"search": query} if query else {}
    data = get_json(REMOTIVE_API, params=params, timeout=20)
    jobs = data.get("jobs", [])
    return jobs[:limit]