from typing import Dict, Any
from .job_model import JobCanonical
from typing import Dict, Any
from .job_model import JobCanonical

def normalize_location(value: str) -> str:
    if not value:
        return "Unknown"
    v = value.strip()
    return v if v else "Unknown"

def normalize_adzuna(job: Dict[str, Any]) -> JobCanonical:
    jid = job.get("id")
    title = job.get("title") or ""
    company = (job.get("company") or {}).get("display_name") or ""
    location = (job.get("location") or {}).get("display_name") or "Unknown"
    description = job.get("description") or ""
    url = job.get("redirect_url") or job.get("url") or ""
    posted_at = job.get("created") or job.get("created_at")

    return JobCanonical(
        id=f"adzuna:{jid}",
        source="adzuna",
        title=title.strip(),
        company=company.strip(),
        location=normalize_location(location),
        description=description.strip(),
        url=url.strip(),
        posted_at=posted_at,
        raw=job,
    )

def normalize_location(value: str) -> str:
    if not value:
        return "Unknown"
    v = value.strip()
    return v if v else "Unknown"

def normalize_remotive(job: Dict[str, Any]) -> JobCanonical:
    jid = job.get("id") or job.get("slug") or job.get("url")
    title = job.get("title") or ""
    company = job.get("company_name") or ""
    location = job.get("candidate_required_location") or "Remote"
    description = job.get("description") or ""
    url = job.get("url") or ""
    posted_at = job.get("publication_date")

    return JobCanonical(
        id=f"remotive:{jid}",
        source="remotive",
        title=title.strip(),
        company=company.strip(),
        location=normalize_location(location),
        description=description.strip(),
        url=url.strip(),
        posted_at=posted_at,
        raw=job,
    )