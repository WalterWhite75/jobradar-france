import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ---- Config (modifiable without touching code) ----
MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8765/rpc")

DEFAULT_QUERY = os.getenv("QUERY", "data analyst")
DEFAULT_LOCATION = os.getenv("LOCATION", "Paris")
DEFAULT_SOURCES = os.getenv("SOURCES", "adzuna,remotive")
DEFAULT_LIMIT = int(os.getenv("LIMIT", "10"))
DEFAULT_TOP_K = int(os.getenv("TOP_K", "3"))

CV_FILE = os.getenv("CV_FILE", "")  # e.g. data/cv_samples/cv_fictif.txt
CV_TEXT_FALLBACK = os.getenv("CV_TEXT", "Python SQL Docker Airflow Power BI")


class McpError(RuntimeError):
    pass


@dataclass
class TraceCall:
    method: str
    tool: Optional[str]
    args: Dict[str, Any]


class McpClient:
    def __init__(self, url: str, timeout_s: int = 45, retries: int = 4):
        self.url = url
        self.timeout_s = timeout_s
        self.retries = retries
        self._id = 0

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})

        last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8")
                out = json.loads(body)

                if out.get("error"):
                    raise McpError(out["error"].get("message", "Unknown MCP error"))
                if "result" not in out:
                    raise McpError("No 'result' field in MCP response")

                return out["result"]

            except (urllib.error.URLError, TimeoutError, ConnectionResetError, McpError) as e:
                last_err = e
                if attempt < self.retries:
                    time.sleep(0.4 * attempt)
                else:
                    raise McpError(f"MCP call failed after {self.retries} attempts: {e}") from e

        raise McpError(str(last_err))

    def initialize(self) -> Dict[str, Any]:
        return self._rpc("initialize", {})

    def tools_list(self) -> Dict[str, Any]:
        return self._rpc("tools/list", {})

    def tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})


def load_cv_text() -> str:
    # MVP: accept TXT content. For PDF, convert to text first.
    if CV_FILE:
        with open(CV_FILE, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return CV_TEXT_FALLBACK


def parse_sources(s: str) -> List[str]:
    parts = [p.strip() for p in (s or "").split(",") if p.strip()]
    return parts or ["adzuna", "remotive"]


def run_agent() -> None:
    client = McpClient(MCP_URL)
    trace: List[TraceCall] = []

    print("\n=== MCP Agent Runner (interop + graph + explain) ===")
    print(f"MCP_URL: {MCP_URL}")

    info = client.initialize()
    print(f"Initialized MCP server: {info}")

    cv_text = load_cv_text()
    if not cv_text.strip():
        raise RuntimeError("CV text is empty. Set CV_TEXT or CV_FILE.")

    query = DEFAULT_QUERY
    location = DEFAULT_LOCATION
    sources = parse_sources(DEFAULT_SOURCES)
    limit = DEFAULT_LIMIT
    top_k = DEFAULT_TOP_K

    # 1) Fetch jobs (interop)
    trace.append(TraceCall("tools/call", "jobs_list", {"query": query, "location": location, "limit": limit, "sources": sources}))
    jobs_res = client.tool_call("jobs_list", {"query": query, "location": location, "limit": limit, "sources": sources})
    jobs = jobs_res.get("jobs", []) or []

    print(f"\n[1] jobs_list -> total={jobs_res.get('count_total', len(jobs))} | by_source={jobs_res.get('count_by_source', {})} | errors={jobs_res.get('errors', {})}")

    jobs = [j for j in jobs if j.get("description")]
    if not jobs:
        print("No jobs with description. Try QUERY=data or QUERY=python")
        return

    # 2) CV skills
    trace.append(TraceCall("tools/call", "cv_extract_skills", {"text": "(cv_text)"}))
    cv_sk = client.tool_call("cv_extract_skills", {"text": cv_text})
    cv_skills = cv_sk.get("skills", []) or []
    print(f"\n[2] CV skills ({len(cv_skills)}): {cv_skills}")

    if not cv_skills:
        print("No skills extracted from CV. Provide a CV with obvious keywords.")
        return

    # 3) Job skills
    jobs_with_skills: List[Dict[str, Any]] = []
    for j in jobs[:limit]:
        # Enrich text to increase extraction robustness
        enriched_text = "\n".join([
            str(j.get("title") or ""),
            str(j.get("company") or ""),
            str(j.get("location") or ""),
            str(j.get("description") or ""),
        ])

        trace.append(TraceCall("tools/call", "job_extract_skills", {"text": "(job.title+company+location+description)"}))
        js = client.tool_call("job_extract_skills", {"text": enriched_text})

        j2 = dict(j)
        j2["skills"] = js.get("skills", []) or []
        jobs_with_skills.append(j2)

    print(f"\n[3] job_extract_skills -> processed {len(jobs_with_skills)} jobs")
    non_empty = [jj for jj in jobs_with_skills if jj.get("skills")]
    print(f"[3bis] jobs with non-empty skills: {len(non_empty)}/{len(jobs_with_skills)}")
    if non_empty:
        sample = non_empty[0]
        print(f"[3bis] sample extracted skills for '{sample.get('title')}' -> {sample.get('skills')}")
    

    # 4) Build graph
    def _build_graph_with_jobs(jobs_ws: List[Dict[str, Any]]):
        trace.append(TraceCall("tools/call", "graph_build", {"cv_skills": cv_skills, "jobs": f"{len(jobs_ws)} jobs"}))
        gb_local = client.tool_call("graph_build", {"cv_skills": cv_skills, "jobs": jobs_ws})
        return gb_local

    gb = _build_graph_with_jobs(jobs_with_skills)
    graph = gb.get("graph")
    summary = gb.get("summary", {})
    print(f"\n[4] graph_build -> {summary}")

    # Fallback strategy if no edges were created (common for very non-technical job descriptions)
    if summary.get("edge_count", 0) == 0:
        fallback_queries = []
        if " " in query.strip():
            fallback_queries.append("data")
        fallback_queries.append("python")

        for fq in fallback_queries:
            print(f"\n[4bis] edge_count=0. Retrying with broader query='{fq}'...")
            query = fq

            trace.append(TraceCall("tools/call", "jobs_list", {"query": query, "location": location, "limit": limit, "sources": sources}))
            jobs_res = client.tool_call("jobs_list", {"query": query, "location": location, "limit": limit, "sources": sources})
            jobs = jobs_res.get("jobs", []) or []
            print(f"[4bis] jobs_list -> total={jobs_res.get('count_total', len(jobs))} | by_source={jobs_res.get('count_by_source', {})} | errors={jobs_res.get('errors', {})}")

            jobs = [j for j in jobs if j.get("description")]
            jobs_with_skills = []
            for j in jobs[:limit]:
                enriched_text = "\n".join([
                    str(j.get("title") or ""),
                    str(j.get("company") or ""),
                    str(j.get("location") or ""),
                    str(j.get("description") or ""),
                ])
                trace.append(TraceCall("tools/call", "job_extract_skills", {"text": "(job.title+company+location+description)"}))
                js = client.tool_call("job_extract_skills", {"text": enriched_text})
                j2 = dict(j)
                j2["skills"] = js.get("skills", []) or []
                jobs_with_skills.append(j2)

            non_empty = [jj for jj in jobs_with_skills if jj.get("skills")]
            print(f"[4bis] jobs with non-empty skills: {len(non_empty)}/{len(jobs_with_skills)}")
            if non_empty:
                sample = non_empty[0]
                print(f"[4bis] sample extracted skills for '{sample.get('title')}' -> {sample.get('skills')}")

            gb = _build_graph_with_jobs(jobs_with_skills)
            graph = gb.get("graph")
            summary = gb.get("summary", {})
            print(f"[4bis] graph_build -> {summary}")

            # Check if graph produces any positive score for CV skills
            tmp_rank = client.tool_call("graph_rank", {"graph": graph, "cv_skills": cv_skills, "top_k": 3})
            best_score = 0.0
            for rr in tmp_rank.get("ranking", []) or []:
                best_score = max(best_score, float(rr.get("score", 0.0)))

            if summary.get("edge_count", 0) > 0 and best_score > 0:
                print(f"[4bis] Fallback successful with query='{fq}' (best_score={best_score}).")
                break
            elif summary.get("edge_count", 0) > 0 and best_score == 0:
                print(f"[4bis] Graph has edges but none overlap CV skills (best_score=0). Trying next fallback...")

    # Rebuild lookup dict after potential fallback
    jobs_by_id = {j["id"]: j for j in jobs_with_skills if j.get("id")}

    # 5) Rank jobs
    trace.append(TraceCall("tools/call", "graph_rank", {"top_k": top_k}))
    gr = client.tool_call("graph_rank", {"graph": graph, "cv_skills": cv_skills, "top_k": top_k})
    ranking = gr.get("ranking", []) or []
    print(f"\n[5] graph_rank -> ranking size={len(ranking)} | meta={gr.get('meta', {})}")

    # 6) Explain top jobs

    print("\n=== TOP RECOMMANDATIONS ===")
    for i, r in enumerate(ranking, start=1):
        job_id = r.get("job_id")
        score = r.get("score", 0.0)
        j = jobs_by_id.get(job_id)
        if not j:
            continue

        trace.append(TraceCall("tools/call", "match_explain", {"job_id": job_id, "score": score}))
        expl = client.tool_call(
            "match_explain",
            {
                "cv_skills": cv_skills,
                "job_skills": j.get("skills", []),
                "job": {"title": j.get("title"), "company": j.get("company")},
                "score": score,
            },
        )

        print(f"\n#{i} — {j.get('title')} | {j.get('company')} | {j.get('location')} | score={score}")
        print("Matched:", ", ".join(expl.get("matched_skills", [])[:12]) or "-")
        print("Missing:", ", ".join(expl.get("missing_skills", [])[:12]) or "-")
        print("Why:", expl.get("why_short"))
        print("URL:", j.get("url"))

    print("\n=== TRACE (audit) ===")
    for t in trace:
        if t.tool:
            print(f"- {t.method} {t.tool} {t.args}")
        else:
            print(f"- {t.method} {t.args}")


if __name__ == "__main__":
    run_agent()