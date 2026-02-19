from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass
class JobCanonical:
    id: str
    source: str
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_at: Optional[str] = None
    employment_type: Optional[str] = None
    remote: Optional[bool] = None
    tags: Optional[List[str]] = None
    raw: Optional[Dict[str, Any]] = None