from server.utils.http import get_json
from server.config import ADZUNA_APP_ID, ADZUNA_APP_KEY, require_adzuna_keys

# Adzuna endpoint (France). Page=1
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/fr/search/1"

def fetch_adzuna_jobs(query: str, location: str = "Paris", limit: int = 10) -> list[dict]:
    """
    Fetch raw jobs from Adzuna.
    """
    require_adzuna_keys()

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "where": location,
        "results_per_page": limit,
        "content-type": "application/json",
    }

    data = get_json(ADZUNA_URL, params=params, timeout=25)
    # Adzuna returns {"results": [...]}
    return data.get("results", [])[:limit]