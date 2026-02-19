from typing import Any, Dict, List, Optional

from server.connectors.remotive import fetch_remotive_jobs
from server.connectors.adzuna import fetch_adzuna_jobs
from server.canonical.normalize import normalize_remotive, normalize_adzuna

SUPPORTED_SOURCES = ["remotive", "adzuna"]


def tools_list() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "jobs_fetch",
                "description": "Fetch raw jobs from a source API (adzuna/remotive).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "enum": SUPPORTED_SOURCES},
                        "query": {"type": "string"},
                        "location": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    },
                    "required": ["source", "query"],
                },
            },
            {
                "name": "jobs_normalize",
                "description": "Normalize raw jobs into JobCanonical format.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "enum": SUPPORTED_SOURCES},
                        "raw": {"type": "array"},
                    },
                    "required": ["source", "raw"],
                },
            },
            {
                "name": "jobs_list",
                "description": "Fetch + normalize jobs from one or many sources.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "location": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string", "enum": SUPPORTED_SOURCES},
                        },
                        "skip_failed_sources": {"type": "boolean"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "cv_extract_skills",
                "description": "Extract skills from a CV text (simple keyword dictionary MVP).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "job_extract_skills",
                "description": "Extract skills from a job description text (same extractor as CV, MVP).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "graph_rank",
                "description": "Rank jobs for a CV using a graph-based model.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cv_skills": {"type": "array", "items": {"type": "string"}},
                        "jobs": {"type": "array", "items": {"type": "object"}},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["cv_skills", "jobs"],
                },
            },
            {
                "name": "match_explain",
                "description": "Explain why a job matches a CV (matched skills, missing skills, readable justification).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cv_skills": {"type": "array", "items": {"type": "string"}},
                        "job_skills": {"type": "array", "items": {"type": "string"}},
                        "job": {"type": "object", "description": "Optional job info (title/company)"},
                        "score": {"type": "number"}
                    },
                    "required": ["cv_skills", "job_skills"],
                },
            },
            {
                "name": "graph_build",
                "description": "Build a bipartite graph Skills<->Jobs (CV skills vs job skills).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cv_skills": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "jobs": {
                            "type": "array",
                            "description": "List of normalized jobs with fields: id, title, source, skills[]"
                        }
                    },
                    "required": ["cv_skills", "jobs"]
                },
            },
            {
                "name": "graph_rank",
                "description": "Rank jobs from a Skills<->Jobs graph using Personalized PageRank (graph theory).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "graph": {
                            "type": "object",
                            "description": "node-link graph produced by graph_build (nx.node_link_data)"
                        },
                        "cv_skills": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "top_k": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["graph", "cv_skills"]
                },
            },
        ]
    }


def _clean_str(v: Any) -> str:
    return (str(v) if v is not None else "").strip()


def _clean_limit(v: Any, default: int = 10) -> int:
    try:
        n = int(v)
    except Exception:
        n = default
    return max(1, min(50, n))


def _normalize_sources(v: Any) -> List[str]:
    """Accepts list[str] or comma-separated string; returns de-duplicated list in stable order."""
    if v is None:
        return ["adzuna", "remotive"]
    if isinstance(v, str):
        parts = [p.strip() for p in v.split(",") if p.strip()]
        v = parts
    if not isinstance(v, list):
        return ["adzuna", "remotive"]

    out: List[str] = []
    for s in v:
        s2 = _clean_str(s)
        if not s2:
            continue
        if s2 not in SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported source: {s2}. Allowed: {SUPPORTED_SOURCES}")
        if s2 not in out:
            out.append(s2)
    return out or ["adzuna", "remotive"]


def _fetch(source: str, query: str, location: str, limit: int) -> List[dict]:
    if source == "remotive":
        return fetch_remotive_jobs(query=query, limit=limit)
    if source == "adzuna":
        return fetch_adzuna_jobs(query=query, location=location, limit=limit)
    raise ValueError(f"Unknown source: {source}")


def _normalize(source: str, raw: List[dict]) -> List[dict]:
    if source == "remotive":
        return [normalize_remotive(j).__dict__ for j in raw]
    if source == "adzuna":
        return [normalize_adzuna(j).__dict__ for j in raw]
    raise ValueError(f"Unknown source: {source}")


def tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Defensive defaults
    arguments = arguments or {}

    if name == "jobs_fetch":
        source = _clean_str(arguments.get("source"))
        if source not in SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported source: {source}. Allowed: {SUPPORTED_SOURCES}")

        query = _clean_str(arguments.get("query"))
        location = _clean_str(arguments.get("location")) or "Paris"
        limit = _clean_limit(arguments.get("limit"), default=10)

        raw = _fetch(source, query, location, limit)
        return {"source": source, "count": len(raw), "raw": raw}

    if name == "jobs_normalize":
        source = _clean_str(arguments.get("source"))
        if source not in SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported source: {source}. Allowed: {SUPPORTED_SOURCES}")

        raw = arguments.get("raw", []) or []
        jobs = _normalize(source, raw)
        return {"source": source, "count": len(jobs), "jobs": jobs}

    if name == "jobs_list":
        query = _clean_str(arguments.get("query"))
        # Remotive search can be strict; default to a broader query if empty.
        if not query:
            query = "data"

        location = _clean_str(arguments.get("location")) or "Paris"
        limit = _clean_limit(arguments.get("limit"), default=10)
        sources = _normalize_sources(arguments.get("sources"))
        skip_failed = bool(arguments.get("skip_failed_sources", True))

        all_jobs: List[dict] = []
        counts: Dict[str, int] = {}
        errors: Dict[str, str] = {}

        for s in sources:
            try:
                raw = _fetch(s, query, location, limit)
                jobs = _normalize(s, raw)
                counts[s] = len(jobs)
                all_jobs.extend(jobs)
            except Exception as e:
                errors[s] = str(e)
                counts[s] = 0
                if not skip_failed:
                    raise

        return {
            "sources": sources,
            "query": query,
            "location": location,
            "count_by_source": counts,
            "count_total": len(all_jobs),
            "errors": errors,
            "jobs": all_jobs,
        }

    if name == "cv_extract_skills":
        from server.cv.extract_skills import extract_skills_with_meta

        text = arguments.get("text") or ""
        return extract_skills_with_meta(text)

    if name == "job_extract_skills":
        from server.cv.extract_skills import extract_skills_with_meta

        text = arguments.get("text") or ""
        return extract_skills_with_meta(text)

    if name == "graph_build":
        from server.graph.build_graph import build_skill_job_graph

        cv_skills = arguments.get("cv_skills") or []
        jobs = arguments.get("jobs") or []

        return build_skill_job_graph(cv_skills=cv_skills, jobs=jobs)

    if name == "graph_rank":
        from server.graph.rank import rank_jobs_from_graph

        graph_obj = arguments.get("graph") or {}
        cv_skills = arguments.get("cv_skills") or []
        top_k = arguments.get("top_k", 10)

        return rank_jobs_from_graph(graph_node_link=graph_obj, seed_skills=cv_skills, top_k=top_k)

    if name == "match_explain":
        from server.graph.explain import explain_match

        cv_skills = arguments.get("cv_skills") or []
        job_skills = arguments.get("job_skills") or []
        job = arguments.get("job") or None
        score = arguments.get("score")

        return explain_match(cv_skills=cv_skills, job_skills=job_skills, job=job, score=score)

    raise ValueError(f"Unknown tool: {name}")