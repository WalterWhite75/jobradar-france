from typing import Any, Dict, List, Optional

class McpClient:
    def __init__(self, url: str, timeout_s: int = 90):
        self.url = url
        self.timeout_s = timeout_s


# -----------------------------
# Filtering & fallback
# -----------------------------

def job_text_blob(job: Dict[str, Any]) -> str:
    parts = [
        str(job.get("title") or ""),
        str(job.get("company") or ""),
        str(job.get("location") or ""),
        str(job.get("description") or ""),
    ]
    return "\n".join(parts)


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = normalize_spaces(text)
    return any(k in t for k in (keywords or []))

# Keywords used for *soft* compliance (we keep jobs even if they don't match)
ROLE_KEYWORDS_FILTER = {
    "data analyst": ["data analyst", "analyst", "reporting", "dashboard", "power bi", "sql"],
    "data scientist": ["data scientist", "machine learning", "ml", "deep learning", "python"],
    "data engineer": ["data engineer", "etl", "pipeline", "airflow", "spark", "python"],
    "business analyst": ["business analyst", "analyste", "métier", "metier", "product", "reporting"],
}

def compute_role_hit(job: Dict[str, Any], role: str) -> bool:
    txt = job_text_blob(job)
    kws = ROLE_KEYWORDS_FILTER.get(role, [])
    return _contains_any(txt, kws)

def compute_contract_hit(job: Dict[str, Any], contract: Optional[str]) -> bool:
    if not contract:
        return True
    txt = job_text_blob(job)
    kw = CONTRACT_KEYWORDS_FILTER.get(contract, [])
    return _contains_any(txt, kw)

def apply_soft_bonus(base_score: float, role_hit: bool, contract: Optional[str], contract_hit: bool) -> float:
    score = float(base_score or 0.0)
    # Bonuses: push compliant jobs up, but don't delete others
    if role_hit:
        score += 0.15
    if contract and contract_hit:
        score += 0.10
    # Small penalty if user asked a contract and job doesn't mention it
    if contract and not contract_hit:
        score -= 0.05
    # clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return round(score, 6)


def run_pipeline(
    client: McpClient,
    role: str,
    location: str,
    contract: Optional[str],
    top_k: int = 10,
    sources: Optional[List[str]] = None,
    trace: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # 1) fetch jobs
    role_query = role or ""
    limit = top_k

    # Fetch a larger pool so we can still return up to `top_k` results after ranking.
    fetch_limit = int(max(limit, top_k * 10, 30))
    fetch_limit = min(fetch_limit, 50)

    jobs_res = safe_call(
        client,
        "jobs_list",
        {
            "query": role_query,
            "location": location,
            "limit": fetch_limit,
            "sources": sources,
            # avoid crashing UI if one source is down
            "skip_failed_sources": True,
        },
        trace,
    )

    jobs = (jobs_res.get("jobs") or [])

    # Keep jobs even if description is empty; we will build a text blob from title/company/location/description.
    # We apply role/contract as *soft* signals later (bonus/penalty), not as hard filters.

    # 2) extract skills from jobs
    jobs_with_skills = []
    # Work on a pool (fetch_limit) but keep compute time bounded
    for j in jobs[:fetch_limit]:
        enriched = "\n".join([
            str(j.get("title") or ""),
            str(j.get("company") or ""),
            str(j.get("location") or ""),
            str(j.get("description") or ""),
        ])

        # Soft compliance flags (do not filter out)
        role_hit = compute_role_hit(j, role)
        contract_hit = compute_contract_hit(j, contract)

        js = safe_call(client, "job_extract_skills", {"text": enriched}, trace)
        j2 = dict(j)
        j2["skills"] = js.get("skills") or []
        j2["role_hit"] = bool(role_hit)
        j2["contract_hit"] = bool(contract_hit)
        jobs_with_skills.append(j2)

    # ... other pipeline steps ...

    # 6) explain
    recos = []
    for r in ranking:
        job_id = r["job_id"]
        score = r["score"]
        j = job_id_to_job.get(job_id)
        if not j:
            continue
        expl = safe_call(client, "match_explain", {"job_id": job_id, "cv_skills": cv_skills}, trace)
        final_score = apply_soft_bonus(score, j.get("role_hit", False), contract, j.get("contract_hit", False))
        recos.append({"job": j, "score": score, "final_score": final_score, "explain": expl})

    # Soft re-ranking: prefer jobs that match the requested role/contract, but keep others.
    recos.sort(key=lambda x: float(x.get("final_score", x.get("score", 0.0))), reverse=True)
    recos = recos[:top_k]

    meta = {
        "method": "pipeline",
        "jobs_list_meta": {
            "pool_size": len(jobs),
            "used_for_scoring": len(jobs_with_skills),
        },
        # ... other meta fields ...
    }

    return {
        "recommendations": recos,
        "meta": meta,
    }


# UI rendering snippet inside Streamlit app:

st.markdown("### ⭐ Recommandations")
for idx, r in enumerate(recos, start=1):
    j = r["job"]
    score = r.get("score", 0.0)
    final_score = float(r.get("final_score", score))
    role_badge = "✅ rôle" if j.get("role_hit") else "⚠️ rôle"
    contract_badge = "✅ contrat" if (contract and j.get("contract_hit")) else ("" if not contract else "⚠️ contrat")
    badges = " ".join([b for b in [role_badge, contract_badge] if b])

    with st.expander(
        f"#{idx} — {j.get('title')} | {j.get('company')} | score={score:.3f} | final={final_score:.3f} | {badges}",
        expanded=(idx == 1),
    ):
        st.write(f"**Compétences extraites (job) :** {j.get('skills')}")
        st.write(f"**Conformité :** role_hit={j.get('role_hit')} | contract_hit={j.get('contract_hit')}")
        # ... other rendering ...