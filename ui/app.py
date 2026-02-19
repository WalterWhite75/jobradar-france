import json
import os
import re
import urllib.request
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple


import streamlit as st

# -----------------------------
# UI theme helpers (visual polish)
# -----------------------------
APP_TITLE = "✨ JobRadar France"
APP_SUBTITLE = "Ton agent conversationnel pour trouver des offres Data/BI pertinentes — et matcher ton CV"

# IMPORTANT: set_page_config must be the first Streamlit command
st.set_page_config(page_title="JobRadar France — Agent Data", layout="wide")

st.markdown(
    """
<style>
  /* Global */
  .block-container {
    padding-top: 2.25rem; /* extra headroom so hero border never clips */
    padding-bottom: 2.5rem;
    padding-left: 1.75rem;
    padding-right: 1.75rem;
    max-width: 1180px;
    margin-left: auto;
    margin-right: auto;
    overflow: visible;
    box-sizing: border-box;
  }
  /* Better overall spacing */
  section.main > div { padding-top: 0.5rem; }
  div[data-testid="stChatInput"] { position: sticky; bottom: 0; background: rgba(10,12,16,0.92); padding-top: 0.75rem; padding-bottom: 0.75rem; border-top: 1px solid rgba(120,120,120,0.18); }
  h1, h2, h3 { letter-spacing: -0.02em; }

  /* Header */
  .hero-wrap {
    padding: 1.0rem;               /* breathing room so border/shadow won't clip */
    margin-top: 0.85rem;           /* avoid top cropping in Streamlit layout */
    margin-bottom: 0.45rem;
    overflow: visible;
  }
  .hero {
    padding: 1.05rem 1.25rem;
    border-radius: 18px;
    background: radial-gradient(1200px 200px at 20% 0%, rgba(33,150,243,0.18), transparent 60%),
                radial-gradient(900px 220px at 85% 40%, rgba(156,39,176,0.18), transparent 60%),
                rgba(255,255,255,0.02);
    border: 1px solid rgba(120,120,120,0.20);
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    margin-bottom: 0;
    margin-top: 0;
    width: 100%;
    box-sizing: border-box;
    overflow: visible;
  }
  .hero-title {
    font-size: clamp(1.35rem, 2.2vw, 1.85rem);
    font-weight: 850;
    margin: 0;
    line-height: 1.15;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
  .hero-sub { margin-top: 0.25rem; opacity: 0.85; }

  /* Prevent any clipping of the hero card */
  section.main, section.main > div { overflow: visible !important; }
  /* Streamlit containers can clip box-shadows/borders on some layouts */
  div[data-testid="stAppViewContainer"],
  div[data-testid="stAppViewBlockContainer"],
  div[data-testid="stVerticalBlock"] {
    overflow: visible !important;
  }

  /* Give a bit of space below the top chrome */
  header[data-testid="stHeader"] { background: transparent; }

  /* Cards */
  .card {
    padding: 0.95rem 1.05rem;
    border-radius: 16px;
    border: 1px solid rgba(120,120,120,0.18);
    background: rgba(255,255,255,0.03);
    box-shadow: 0 10px 26px rgba(0,0,0,0.20);
  }
  .muted { opacity: 0.75; }
  .small { font-size: 0.92rem; }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    border: 1px solid rgba(120,120,120,0.22);
    font-size: 0.82rem;
    margin-right: 0.35rem;
    margin-bottom: 0.25rem;
    background: rgba(255,255,255,0.04);
  }
  .badge-ok { border-color: rgba(46, 204, 113, 0.55); }
  .badge-warn { border-color: rgba(241, 196, 15, 0.60); }
  .badge-info { border-color: rgba(52, 152, 219, 0.55); }

  /* Job title */
  .job-title { font-weight: 750; font-size: 1.02rem; margin: 0; }
  .job-meta { margin-top: 0.25rem; opacity: 0.85; }
  .job-url a { text-decoration: none; font-weight: 650; }

  /* Divider */
  .thin-hr { border: none; border-top: 1px solid rgba(120,120,120,0.22); margin: 0.75rem 0; }

  /* Sidebar polish */
  section[data-testid="stSidebar"] .block-container { padding-top: 0.9rem; }
  section[data-testid="stSidebar"] h3 { margin-top: 0.4rem; }
  section[data-testid="stSidebar"] .stSlider, section[data-testid="stSidebar"] .stTextInput { margin-bottom: 0.35rem; }

  /* Make expander headers cleaner */
  div[data-testid="stExpander"] details summary { font-weight: 650; }

  /* Improve chat bubbles slightly */
  div[data-testid="stChatMessage"] { margin-top: 0.4rem; }
  div[data-testid="stChatMessage"] .stMarkdown { line-height: 1.35; }
</style>
""",
    unsafe_allow_html=True,
)


def _badge(text: str, kind: str = "info") -> str:
    cls = {"ok": "badge badge-ok", "warn": "badge badge-warn", "info": "badge badge-info"}.get(kind, "badge")
    return f"<span class='{cls}'>{text}</span>"


def _clip(s: str, n: int = 280) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


def _safe_md(text: str) -> str:
    return (text or "").replace("<", "&lt;").replace(">", "&gt;")


def _job_card_header(title: str, company: str, location: str) -> str:
    return (
        f"<p class='job-title'>{title}</p>"
        f"<div class='job-meta small'>🏢 {company} &nbsp; • &nbsp; 📍 {location}</div>"
    )


# -----------------------------
# Config
# -----------------------------
MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8765/rpc")
DEFAULT_LOCATION = os.getenv("LOCATION", "Paris")
DEFAULT_SOURCES = os.getenv("SOURCES", "adzuna,remotive")
DEFAULT_LIMIT = int(os.getenv("LIMIT", "20"))
DEFAULT_TOP_K = int(os.getenv("TOP_K", "5"))


CV_TEXT_FALLBACK = os.getenv("CV_TEXT", "Python SQL Docker Airflow Power BI")

# Country config (hard filter)
DEFAULT_COUNTRY = os.getenv("COUNTRY", "France")


# -----------------------------
# MCP Client
# -----------------------------
class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, url: str, timeout_s: int = 45, retries: int = 3, backoff_s: float = 0.8):
        self.url = url
        self.timeout_s = timeout_s
        self.retries = retries
        self.backoff_s = backoff_s
        self._id = 0

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import time

        last_exc: Exception | None = None

        for attempt in range(self.retries + 1):
            self._id += 1
            payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})

            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    out = json.loads(resp.read().decode("utf-8"))
            except TimeoutError as e:
                last_exc = e
            except Exception as e:
                last_exc = e
            else:
                if out.get("error"):
                    raise McpError(out["error"].get("message", "Unknown MCP error"))
                if "result" not in out:
                    raise McpError("No 'result' field in MCP response")
                return out["result"]

            if attempt < self.retries:
                time.sleep(self.backoff_s * (attempt + 1))

        raise McpError(f"HTTP/MCP error: timed out after {self.retries+1} attempts (timeout={self.timeout_s}s). Last: {last_exc!r}")

    def initialize(self) -> Dict[str, Any]:
        return self._rpc("initialize", {})

    def tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})



# -----------------------------
# Text utils
# -----------------------------
def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def job_text_blob(job: Dict[str, Any]) -> str:
    parts = [
        str(job.get("title") or ""),
        str(job.get("company") or ""),
        str(job.get("location") or ""),
        str(job.get("description") or ""),
    ]
    return normalize_spaces(" ".join(parts))


# --- Location utils for country filtering ---

def job_location_blob(job: Dict[str, Any]) -> str:
    """Best-effort location string for filtering."""
    loc = str(job.get("location") or "")
    raw = job.get("raw") or {}
    # Adzuna often stores a richer location object
    try:
        if isinstance(raw, dict):
            rloc = raw.get("location") or {}
            if isinstance(rloc, dict):
                loc = loc or str(rloc.get("display_name") or "")
                area = rloc.get("area")
                if isinstance(area, list) and area:
                    # prepend country when available
                    loc = " ".join([str(a) for a in area if a]) + (" " + loc if loc else "")
    except Exception:
        pass
    return normalize_spaces(loc)


FRANCE_LOCATION_HINTS = [
    "france",
    "ile-de-france",
    "île-de-france",
    "paris",
    "lyon",
    "marseille",
    "toulouse",
    "lille",
    "bordeaux",
    "nantes",
    "rennes",
    "nice",
    "strasbourg",
    "montpellier",
    "grenoble",
]


def filter_jobs_france_only(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hard filter to keep only France-based jobs.

    Motivation: some sources (esp. remote/global boards) can return US/Worldwide results even when
    the query is a French city. We keep only jobs whose location strongly indicates France.
    """
    out: List[Dict[str, Any]] = []
    for j in jobs:
        loc = job_location_blob(j)
        # If location is missing, we cannot safely assume France.
        if not loc:
            continue
        if any(h in loc for h in FRANCE_LOCATION_HINTS):
            out.append(j)
    return out


# -----------------------------
# Strict contract filtering based on TITLE
# -----------------------------
# User requirement:
# - If user does NOT ask for stage/alternance: exclude stage/alternance offers
# - If user asks for stage: keep ONLY stage/internship offers (title-based)
# - If user asks for alternance: keep ONLY alternance/apprenticeship offers (title-based)
def job_title_blob(job: Dict[str, Any]) -> str:
    return normalize_spaces(str(job.get("title") or ""))

INTERNSHIP_TITLE_KW = [
    "stage",
    "stagiaire",
    "intern",
    "internship",
]

APPRENTICESHIP_TITLE_KW = [
    "alternance",
    "apprentissage",
    "apprenti",
    "apprenticeship",
    "apprentice",
]


def _title_contains_any(title: str, kws: List[str]) -> bool:
    return any(k in title for k in kws)


def is_stage_title(job: Dict[str, Any]) -> bool:
    return _title_contains_any(job_title_blob(job), INTERNSHIP_TITLE_KW)


def is_alternance_title(job: Dict[str, Any]) -> bool:
    return _title_contains_any(job_title_blob(job), APPRENTICESHIP_TITLE_KW)


def is_intern_or_apprentice_title(job: Dict[str, Any]) -> bool:
    return is_stage_title(job) or is_alternance_title(job)


def apply_contract_title_filter(jobs: List[Dict[str, Any]], contract: Optional[str]) -> List[Dict[str, Any]]:
    """Apply the strict contract rule using ONLY the job title."""
    if contract == "stage":
        return [j for j in jobs if is_stage_title(j)]
    if contract == "alternance":
        return [j for j in jobs if is_alternance_title(j)]

    # Default behavior (including CDI/CDD or unspecified): exclude internships/apprenticeships
    return [j for j in jobs if not is_intern_or_apprentice_title(j)]


# -----------------------------
# Intent parsing
# -----------------------------
ROLE_ALIASES = {
    "data analyst": [
        "data analyst",
        "analyste data",
        "analyste de données",
        "data analytics",
        "reporting",
        "dashboard",
        "power bi",
        "tableau",
    ],
    "data scientist": [
        "data scientist",
        "datascientist",
        "machine learning",
        "ml",
        "deep learning",
        "nlp",
        "computer vision",
    ],
    "data engineer": [
        "data engineer",
        "ingénieur data",
        "data engineering",
        "etl",
        "pipeline",
        "airflow",
        "spark",
        "dbt",
    ],
    "business analyst": [
        "business analyst",
        "analyste métier",
        "analyste business",
        "product analyst",
        "amoa",
        "moa",
        "fonctionnel",
    ],
}

CONTRACT_ALIASES = {
    "cdi": ["cdi", "permanent", "full time", "full-time", "temps plein"],
    "cdd": ["cdd", "fixed-term", "fixed term", "contrat à durée déterminée"],
    "stage": ["stage", "intern", "internship", "stagiaire"],
    "alternance": ["alternance", "apprenticeship", "apprenti", "apprentissage"],
}

CONTRACT_KEYWORDS_FILTER = {
    # on garde large mais pas débile
    "stage": ["stage", "intern", "internship", "stagiaire"],
    "alternance": ["alternance", "apprenticeship", "apprenti", "apprentissage"],
    "cdi": ["cdi", "permanent", "temps plein", "full time", "full-time"],
    "cdd": ["cdd", "fixed term", "fixed-term", "contrat à durée déterminée"],
}

ROLE_KEYWORDS_FILTER = {
    "data analyst": ["data analyst", "analyste", "reporting", "dashboard", "power bi", "tableau", "sql"],
    "data scientist": ["data scientist", "machine learning", "ml", "deep learning", "model", "python"],
    "data engineer": ["data engineer", "etl", "pipeline", "airflow", "spark", "dbt", "ingénieur data"],
    "business analyst": ["business analyst", "analyste métier", "amoa", "moa", "fonctionnel", "product"],
}


def detect_role(user_text: str) -> str:
    t = normalize_spaces(user_text)
    for role, aliases in ROLE_ALIASES.items():
        for a in aliases:
            if a in t:
                return role
    # fallback simple
    if "scientist" in t or "machine learning" in t or re.search(r"\bml\b", t):
        return "data scientist"
    if "engineer" in t or "etl" in t or "pipeline" in t:
        return "data engineer"
    if "business" in t or "amoa" in t or "moa" in t or "métier" in t or "metier" in t:
        return "business analyst"
    return "data analyst"


def detect_contract(user_text: str) -> Optional[str]:
    t = normalize_spaces(user_text)
    for c, aliases in CONTRACT_ALIASES.items():
        for a in aliases:
            if a in t:
                return c
    return None


def detect_location(user_text: str) -> str:
    t = normalize_spaces(user_text)
    if "remote" in t or "télétravail" in t or "teletravail" in t:
        return "Remote"

    # patterns: "à Lyon" / "a Lyon" / "sur Lyon"
    m = re.search(r"\b(?:à|a|sur)\s+([a-zA-ZÀ-ÿ\- ]{2,30})\b", user_text)
    if m:
        city = m.group(1).strip()
        city = re.sub(r"\b(en|pour|sur|avec|de)$", "", city, flags=re.IGNORECASE).strip()
        if len(city) >= 2:
            return city

    return DEFAULT_LOCATION


def parse_user_intent(user_text: str) -> Dict[str, Any]:
    return {
        "role": detect_role(user_text),
        "contract": detect_contract(user_text),
        "location": detect_location(user_text),
    }


# -----------------------------
# Query building
# -----------------------------
def build_mcp_query(role: str, contract: Optional[str], location: str) -> str:
    """Build the query sent to MCP jobs_list.

    Important: we keep the query *role-focused*.
    Contract and location are already handled by dedicated params or post-filters.

    Mixing contract/location tokens into the query often collapses recall (few results,
    repeated results) depending on the upstream job APIs.
    """
    return (role or "").strip()


ROLE_FALLBACK_QUERIES = {
    "data analyst": ["data analyst", "sql", "power bi", "reporting"],
    "data scientist": ["data scientist", "machine learning", "python"],
    "data engineer": ["data engineer", "etl", "airflow", "python"],
    "business analyst": ["business analyst", "amoa", "moa", "fonctionnel", "product analyst"],
}


# -----------------------------
# Filters / soft scoring (do NOT drop jobs)
# -----------------------------

def _contains_any(txt: str, keywords: List[str]) -> bool:
    return any(k in txt for k in keywords)


def role_match_flag(job: Dict[str, Any], role: str) -> bool:
    kw = ROLE_KEYWORDS_FILTER.get(role, [])
    if not kw:
        return True
    return _contains_any(job_text_blob(job), kw)



def contract_match_flag(job: Dict[str, Any], contract: Optional[str]) -> bool:
    """Contract compliance flag.

    IMPORTANT: For stage/alternance we rely strictly on TITLE to avoid false positives.
    For other cases (None/CDI/CDD), we exclude stage/alternance titles by default.

    Note: CDI/CDD are often unreliable in upstream APIs; we keep them as soft signals.
    """
    if contract == "stage":
        return is_stage_title(job)
    if contract == "alternance":
        return is_alternance_title(job)

    # Default: user did not ask for internship/apprenticeship => reject those titles
    if is_intern_or_apprentice_title(job):
        return False

    # For CDI/CDD (or None), keep previous broad matching as a soft signal.
    if not contract or contract not in CONTRACT_KEYWORDS_FILTER:
        return True

    kw = CONTRACT_KEYWORDS_FILTER.get(contract, [])
    if not kw:
        return True
    return _contains_any(job_text_blob(job), kw)


def compute_job_soft_bonus(job: Dict[str, Any], role: str, contract: Optional[str], strict_filters: bool) -> float:
    """Score adjustment layered on top of the graph score.

    - If strict_filters=True: penalize offers that don't match the requested role/contract.
      (We still keep them as fallback if the pool is small.)
    - If strict_filters=False: give small positive bumps to compliant offers.

    This makes strict/relaxed modes actually affect ranking.
    """
    role_ok = role_match_flag(job, role)
    contract_ok = contract_match_flag(job, contract)

    if strict_filters:
        bonus = 0.0
        if not role_ok:
            bonus -= 0.30
        if contract and not contract_ok:
            bonus -= 0.30
        return bonus

    bonus = 0.0
    if role_ok:
        bonus += 0.10
    if contract and contract_ok:
        bonus += 0.10
    return bonus


def annotate_job_flags(job: Dict[str, Any], role: str, contract: Optional[str]) -> Dict[str, Any]:
    j2 = dict(job)
    j2["role_hit"] = bool(role_match_flag(job, role))
    j2["contract_hit"] = bool(contract_match_flag(job, contract))
    return j2

# Deterministic fallback ranking function
def fallback_rank_score(job: Dict[str, Any], cv_skills: List[str], role: str, contract: Optional[str], strict_filters: bool) -> float:
    """Deterministic fallback score when graph_rank is sparse.

    Priorities:
    1) Role compliance
    2) Contract compliance (if requested)
    3) Skill overlap

    Returns a score in [0, 1].
    """
    cv_set = set(cv_skills or [])
    job_set = set(job.get("skills") or [])
    overlap = len(cv_set.intersection(job_set))
    overlap_ratio = overlap / max(1, len(cv_set))

    role_ok = bool(job.get("role_hit"))
    contract_ok = bool(job.get("contract_hit")) if contract else True

    # Base: overlap (0..1)
    score = overlap_ratio

    # Compliance weights
    if role_ok:
        score += 0.35
    elif strict_filters:
        score -= 0.10

    if contract:
        if contract_ok:
            score += 0.25
        elif strict_filters:
            score -= 0.10

    # Clamp
    return max(0.0, min(1.0, score))


# -----------------------------
# CV extraction (PDF/TEX/TXT/DOCX + OCR optionnel)
# -----------------------------
def _pdf_extract_text(pdf_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text from a PDF.

    Strategy:
    1) pypdf (often robust)
    2) pdfplumber (layout-aware)
    3) PyPDF2 (fallback)

    Returns: (text, debug_dict)
    """
    debug: Dict[str, Any] = {"mode": "pdf-text", "pages": None, "errors": []}

    # 0) pypdf (preferred)
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(pdf_bytes))
        debug["pages"] = len(reader.pages)
        parts: List[str] = []
        for p in reader.pages:
            parts.append(p.extract_text() or "")
        txt = "\n".join(parts).strip()
        if txt:
            return txt, debug
    except Exception as e:
        debug["errors"].append(f"pypdf: {repr(e)}")

    # 1) pdfplumber
    try:
        import pdfplumber  # type: ignore

        parts = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            debug["pages"] = debug["pages"] or len(pdf.pages)
            for p in pdf.pages:
                parts.append(p.extract_text() or "")
        txt = "\n".join(parts).strip()
        if txt:
            return txt, debug
    except Exception as e:
        debug["errors"].append(f"pdfplumber: {repr(e)}")

    # 2) PyPDF2 (last resort)
    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(pdf_bytes))
        debug["pages"] = debug["pages"] or len(reader.pages)
        pages = [(p.extract_text() or "") for p in reader.pages]
        txt = "\n".join(pages).strip()
        return txt, debug
    except Exception as e:
        debug["errors"].append(f"PyPDF2: {repr(e)}")

    return "", debug




def _read_uploaded_as_text(uploaded) -> Tuple[str, Dict[str, Any]]:
    name = (uploaded.name or "").lower()
    data = uploaded.getvalue() or b""
    debug: Dict[str, Any] = {"file": name, "bytes": len(data), "steps": []}

    if not data:
        debug["steps"].append({"mode": "empty", "ok": False})
        return "", debug

    # PDF
    if name.endswith(".pdf"):
        txt, d1 = _pdf_extract_text(data)
        debug["steps"].append({"mode": "pdf-text", **d1, "chars": len(txt)})
        return txt, debug

    # DOCX
    if name.endswith(".docx"):
        try:
            import docx  # type: ignore
            doc = docx.Document(BytesIO(data))
            txt = "\n".join([p.text for p in doc.paragraphs]).strip()
            debug["steps"].append({"mode": "docx", "chars": len(txt)})
            return txt, debug
        except Exception as e:
            debug["steps"].append({"mode": "docx", "error": repr(e)})
            return "", debug

    # TEX/TXT (ou tout autre texte)
    try:
        txt = data.decode("utf-8", errors="ignore").strip()
        debug["steps"].append({"mode": "text", "chars": len(txt)})
        return txt, debug
    except Exception as e:
        debug["steps"].append({"mode": "text", "error": repr(e)})
        return "", debug


# -----------------------------
# UI helpers
# -----------------------------
def parse_sources(s: str) -> List[str]:
    parts = [p.strip() for p in (s or "").split(",") if p.strip()]
    return parts or ["adzuna", "remotive"]


def safe_call(client: McpClient, tool: str, args: Dict[str, Any], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    trace.append({"tool": tool, "args": args})
    try:
        return client.tool_call(tool, args)
    except Exception as e:
        return {"_error": str(e), "_tool": tool, "_args": args}


def load_cv_text_from_ui(client: McpClient) -> Tuple[str, Dict[str, Any], List[str]]:
    st.sidebar.subheader("CV")

    uploaded = st.sidebar.file_uploader(
        "Uploader un CV (PDF/TEX/TXT/DOCX)",
        type=["pdf", "tex", "txt", "docx"],
    )

    extracted = ""
    debug_info: Dict[str, Any] = {"status": "no_file"}

    if uploaded is not None:
        extracted, debug_info = _read_uploaded_as_text(uploaded)
        st.sidebar.caption(f"Texte extrait : {len(extracted)} caractères")

        if not extracted:
            st.sidebar.warning(
                "Impossible d'extraire du texte.\n\n"
                "➡️ Ouvre '🔧 Debug extraction' pour voir l'erreur exacte.\n\n"
                "Ça arrive si:\n"
                "- PDF scanné (image)\n"
                "- libs PDF non installées dans le même env que Streamlit\n"
            )

        with st.sidebar.expander("🔧 Debug extraction", expanded=False):
            st.sidebar.json(debug_info)

    # Fallback: allow manual paste/edit ONLY if needed
    with st.sidebar.expander("📋 Coller / éditer le CV (fallback)", expanded=False):
        cv_text = st.text_area(
            "CV (texte)",
            value=(extracted or CV_TEXT_FALLBACK),
            height=220,
        )

    # If user never opens the expander, we still need a cv_text value
    if "cv_text" not in locals():
        cv_text = (extracted or CV_TEXT_FALLBACK)

    # Store raw CV text for debugging if needed
    st.session_state["cv_text_raw"] = cv_text

    # Show ONLY technical skills extracted from CV
    cv_skills: List[str] = []
    try:
        res = client.tool_call("cv_extract_skills", {"text": cv_text})
        cv_skills = res.get("skills") or []
    except Exception:
        cv_skills = []

    st.sidebar.markdown("### 🧰 Compétences techniques détectées")
    if cv_skills:
        badges = " ".join([_badge(s, "info") for s in cv_skills[:60]])
        st.sidebar.markdown(badges, unsafe_allow_html=True)
        if len(cv_skills) > 60:
            st.sidebar.caption(f"+{len(cv_skills) - 60} autres…")
    else:
        st.sidebar.warning("Aucune compétence détectée (vérifie le texte extrait / mapping).")

    # Optional: show raw text for debugging
    show_raw = st.sidebar.toggle("Afficher le texte brut (debug)", value=False)
    if show_raw:
        with st.sidebar.expander("🧾 Texte CV (debug)", expanded=False):
            st.sidebar.text_area("Texte", value=cv_text[:20000], height=220)

    return cv_text, debug_info, cv_skills


# -----------------------------
# Core pipeline
# -----------------------------
def run_pipeline(
    client: McpClient,
    cv_text: str,
    role: str,
    contract: Optional[str],
    location: str,
    sources: List[str],
    limit: int,
    top_k: int,
    query: str,
    strict_filters: bool = True,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    trace: List[Dict[str, Any]] = []

    # 1) Fetch jobs
    jobs_res = safe_call(
        client,
        "jobs_list",
        {
            "query": query,
            "location": location,
            # fetch a bigger pool so we can still return top_k after ranking
            "limit": max(limit, top_k * 10, 30),
            "sources": sources,
            "skip_failed_sources": True,
        },
        trace,
    )
    if jobs_res.get("_error"):
        meta = {
            "query_used": query,
            "role": role,
            "contract": contract,
            "location": location,
            "strict_filters": strict_filters,
            "jobs_list_meta": {
                "error": jobs_res["_error"],
                "tool": jobs_res.get("_tool"),
                "args": jobs_res.get("_args"),
            },
            "graph_summary": {},
            "trace": trace,
        }
        return meta, []
    jobs = (jobs_res.get("jobs") or [])

    # 🇫🇷 Hard country filter: keep only France jobs to avoid US/Worldwide noise
    jobs_before_country = len(jobs)
    jobs = filter_jobs_france_only(jobs)
    jobs_after_country = len(jobs)

    # Keep jobs even if description is missing; we can still extract from title/company/location.
    jobs_before = len(jobs)

    # ✅ Strict contract filtering based on TITLE (user requirement)
    jobs = apply_contract_title_filter(jobs, contract)
    jobs_after_title_contract_filter = len(jobs)

    # Soft flags (do NOT drop)
    jobs = [annotate_job_flags(j, role, contract) for j in jobs]

    # counts for observability
    jobs_after_role = sum(1 for j in jobs if j.get("role_hit"))
    jobs_after_contract = sum(1 for j in jobs if j.get("contract_hit"))

    # 2) CV skills
    cv_sk = safe_call(client, "cv_extract_skills", {"text": cv_text}, trace)
    cv_skills = cv_sk.get("skills") or []

    # Process only the first N jobs for extraction (still uses pool fetched above)
    jobs_with_skills = []
    for j in jobs[: max(limit, top_k * 10, 30)]:
        enriched = "\n".join(
            [
                str(j.get("title") or ""),
                str(j.get("company") or ""),
                str(j.get("location") or ""),
                str(j.get("description") or ""),
            ]
        )
        js = safe_call(client, "job_extract_skills", {"text": enriched}, trace)
        j2 = dict(j)
        j2["skills"] = js.get("skills") or []
        jobs_with_skills.append(j2)

    # 4) graph build
    gb = safe_call(client, "graph_build", {"cv_skills": cv_skills, "jobs": jobs_with_skills}, trace)
    graph = gb.get("graph")
    summary = gb.get("summary") or {}

    # 5) rank
    gr = safe_call(client, "graph_rank", {"graph": graph, "cv_skills": cv_skills, "top_k": top_k}, trace)
    ranking = gr.get("ranking") or []

    # 6) explain
    jobs_by_id = {j.get("id"): j for j in jobs_with_skills if j.get("id")}

    # Re-rank with soft bonus (do not change MCP score, just prioritize compliant jobs)
    rescored = []
    for r in ranking:
        job_id = r.get("job_id")
        base_score = float(r.get("score", 0.0))
        j = jobs_by_id.get(job_id)
        if not j:
            continue
        bonus = compute_job_soft_bonus(j, role, contract, strict_filters)
        final_score = min(1.0, base_score + bonus)
        rescored.append({"job_id": job_id, "base_score": base_score, "bonus": bonus, "final_score": final_score})

    rescored.sort(key=lambda x: x["final_score"], reverse=True)

    # If graph_rank is sparse (few edges / few ranked items), build a complete ranking from the pool.
    if len(rescored) < top_k:
        existing_ids = {x["job_id"] for x in rescored}
        for j in jobs_with_skills:
            job_id = j.get("id")
            if not job_id or job_id in existing_ids:
                continue

            base_score = fallback_rank_score(j, cv_skills, role, contract, strict_filters)
            bonus = compute_job_soft_bonus(j, role, contract, strict_filters)
            final_score = max(0.0, min(1.0, base_score + bonus))

            rescored.append({
                "job_id": job_id,
                "base_score": float(base_score),
                "bonus": float(bonus),
                "final_score": float(final_score),
            })

        rescored.sort(key=lambda x: x["final_score"], reverse=True)

    recos = []
    for r in rescored[:top_k]:
        job_id = r["job_id"]
        j = jobs_by_id.get(job_id)
        if not j:
            continue
        expl = safe_call(
            client,
            "match_explain",
            {
                "cv_skills": cv_skills,
                "job_skills": j.get("skills") or [],
                "job": {"title": j.get("title"), "company": j.get("company")},
                "score": float(r["final_score"]),
            },
            trace,
        )
        recos.append(
            {
                "job": j,
                "score": float(r["final_score"]),
                "score_base": float(r["base_score"]),
                "score_bonus": float(r["bonus"]),
                "explain": expl,
            }
        )

    meta = {
        "query_used": query,
        "role": role,
        "contract": contract,
        "location": location,
        "strict_filters": strict_filters,
        "jobs_list_meta": {
            "count_total": jobs_res.get("count_total"),
            "count_by_source": jobs_res.get("count_by_source"),
            "errors": jobs_res.get("errors"),
            "pool_size": jobs_before,
            "before_country_filter": jobs_before_country,
            "after_country_filter": jobs_after_country,
            "after_title_contract_filter": jobs_after_title_contract_filter,
            "role_hit_count": jobs_after_role,
            "contract_hit_count": jobs_after_contract,
            "jobs_with_skills": len(jobs_with_skills),
            "ranked_count": len(rescored),
            "returned_top_k": min(top_k, len(rescored)),
        },
        "graph_summary": summary,
        "trace": trace,
    }
    return meta, recos


def run_with_fallbacks(
    client: McpClient,
    cv_text: str,
    role: str,
    contract: Optional[str],
    location: str,
    sources: List[str],
    limit: int,
    top_k: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Stratégie :
    1) Query = role + contract + location (strict filters)
    2) Fallback queries (strict)
    3) Si toujours vide -> relâcher strict_filters (role/contract), mais garder query informative
    """
    tried: List[Dict[str, Any]] = []

    base_query = build_mcp_query(role, contract, location)
    candidates = [base_query] + ROLE_FALLBACK_QUERIES.get(role, []) + [role, "data"]

    best_meta: Optional[Dict[str, Any]] = None
    best_recos: List[Dict[str, Any]] = []
    best_quality = -1.0

    # Pass 1: strict
    for q in candidates:
        meta, recos = run_pipeline(
            client=client,
            cv_text=cv_text,
            role=role,
            contract=contract,
            location=location,
            sources=sources,
            limit=limit,
            top_k=top_k,
            query=q,
            strict_filters=True,
        )
        tried.append({"query": q, "strict": True, "top1": (recos[0]["score"] if recos else 0.0)})

        top1 = recos[0]["score"] if recos else 0.0
        edges = float((meta.get("graph_summary") or {}).get("edge_count", 0))
        quality = float(top1) + (0.05 if edges > 0 else 0.0)

        if quality > best_quality:
            best_quality = quality
            best_meta, best_recos = meta, recos

        # stop if we have decent results
        if recos:
            best_meta["fallback_tried"] = tried
            return best_meta, best_recos

    # Pass 2: relaxed filters (avoid "Aucune reco exploitable" too often)
    for q in candidates:
        meta, recos = run_pipeline(
            client=client,
            cv_text=cv_text,
            role=role,
            contract=contract,
            location=location,
            sources=sources,
            limit=limit,
            top_k=top_k,
            query=q,
            strict_filters=False,
        )
        tried.append({"query": q, "strict": False, "top1": (recos[0]["score"] if recos else 0.0)})

        top1 = recos[0]["score"] if recos else 0.0
        edges = float((meta.get("graph_summary") or {}).get("edge_count", 0))
        quality = float(top1) + (0.05 if edges > 0 else 0.0)

        if quality > best_quality:
            best_quality = quality
            best_meta, best_recos = meta, recos

        if recos:
            best_meta["fallback_tried"] = tried
            return best_meta, best_recos

    if best_meta is None:
        best_meta = {"fallback_tried": tried}
    else:
        best_meta["fallback_tried"] = tried

    return best_meta, best_recos


# -----------------------------
# Streamlit UI
# -----------------------------
st.markdown(
    f"""
<div class='hero-wrap'>
  <div class='hero'>
    <div class='hero-title'>🤖 {APP_TITLE}</div>
    <div class='hero-sub'>{APP_SUBTITLE}</div>
    <div class='small muted' style='margin-top:0.55rem'>
      Décris ta recherche (rôle + contrat + ville). Exemple : <b>"Stage data analyst à Paris"</b>.
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# MCP client must be initialized before sidebar so sidebar can call cv_extract_skills
client = McpClient(MCP_URL)
try:
    info = client.initialize()
except Exception as e:
    st.error(f"Serveur MCP injoignable: {e}")
    st.stop()

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown(
        f"""
<div class='card small'>
  <div><b>Serveur</b>: <span class='muted'>{_safe_md(MCP_URL)}</span></div>
  <div><b>Pays</b>: <span class='muted'>{_safe_md(DEFAULT_COUNTRY)}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )

    sources = parse_sources(st.text_input("Sources (csv)", DEFAULT_SOURCES))
    limit = st.slider("Pool (offres analysées)", 5, 30, min(DEFAULT_LIMIT, 30))
    top_k = st.slider("Résultats affichés (Top K)", 1, 10, min(DEFAULT_TOP_K, 10))

    # Guardrail: Top K cannot exceed the pool
    if top_k > limit:
        st.warning("Top K ne peut pas être supérieur au nombre d'offres analysées. Ajustement automatique.")
        top_k = limit

    st.caption("Pool = analyse (skills + matching). Top K = affichage. Top K ≤ Pool.")

    st.divider()
    st.markdown("### 🧪 Mode développeur")
    debug_mode = st.toggle("Afficher les infos techniques (meta/trace)", value=False)
    st.caption("Désactive pour une interface clean. Active seulement pour diagnostiquer.")

    st.divider()
    cv_text, cv_debug, cv_skills_ui = load_cv_text_from_ui(client)
    st.divider()

    st.markdown("### Exemples de demandes")
    st.code("Je cherche un stage data analyst à Paris")
    st.code("Je veux une alternance data engineer à Lyon")
    st.code("CDI data scientist remote")
    st.code("CDD business analyst à Lyon")


# Show MCP server status after sidebar
st.markdown("<div class='card'>", unsafe_allow_html=True)
colA, colB = st.columns([1.35, 2.0])
with colA:
    st.markdown(
        f"**✅ Serveur MCP**<br><span class='muted small'>{info.get('name')} v{info.get('version')}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        " ".join([
            _badge(f"Sources: {len(sources) if isinstance(sources, list) else 0}", "info"),
            _badge(f"Pool: {int(limit)}", "info"),
            _badge(f"Top K: {int(top_k)}", "info"),
        ]),
        unsafe_allow_html=True,
    )
with colB:
    st.markdown(
        "<div class='small muted'>\n"
        "Le <b>Pool</b> est le nombre d’offres analysées (extraction + matching). \n"
        "Le <b>Top K</b> est le nombre d’offres affichées dans les résultats.\n"
        "</div>",
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Dis-moi ce que tu cherches (rôle + contrat + lieu).\nExemples: 'Stage data analyst à Paris', 'CDD business analyst à Lyon', 'Alternance data engineer à Paris'.",
        }
    ]


# Display chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Empty-state: give the user something to do immediately
if len(st.session_state.messages) == 1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 🚀 Démarrage rapide")
    st.markdown(
        """
1) Vérifie que le serveur MCP tourne.
2) (Optionnel) Upload ton CV.
3) Écris une demande dans la barre en bas.
"""
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button("Stage data analyst à Paris", use_container_width=True, on_click=lambda: st.session_state.update({'_quick_prompt': "Stage data analyst à Paris"}))
    with c2:
        st.button("Alternance data engineer à Lyon", use_container_width=True, on_click=lambda: st.session_state.update({'_quick_prompt': "Alternance data engineer à Lyon"}))
    with c3:
        st.button("CDI data scientist à Paris", use_container_width=True, on_click=lambda: st.session_state.update({'_quick_prompt': "CDI data scientist à Paris"}))
    with c4:
        st.button("CDD business analyst à Lyon", use_container_width=True, on_click=lambda: st.session_state.update({'_quick_prompt': "CDD business analyst à Lyon"}))
    st.markdown("</div>", unsafe_allow_html=True)

_default_q = st.session_state.pop("_quick_prompt", None)
prompt = st.chat_input(
    "Ex: 'CDD business analyst à Lyon' / 'Alternance data engineer à Paris' / 'CDI data scientist remote' ...",
    key="chat_input",
)
# If a quick button was clicked, simulate a prompt submission
if _default_q and not prompt:
    prompt = _default_q

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    intent = parse_user_intent(prompt)
    role = intent["role"]
    contract = intent["contract"]
    location = intent["location"]

    with st.chat_message("assistant"):
        st.markdown("🔎 J’analyse ta demande…")
        intent_badges = " ".join(
            [
                _badge(f"Rôle: {role}", "info"),
                _badge(f"Contrat: {contract or '—'}", "info"),
                _badge(f"Lieu: {location}", "info"),
            ]
        )
        st.markdown(f"<div class='card'>{intent_badges}</div>", unsafe_allow_html=True)

        if not cv_text.strip():
            st.error("CV vide. Upload un CV ou colle le texte dans la sidebar.")
            st.stop()

        try:
            meta, recos = run_with_fallbacks(
                client=client,
                cv_text=cv_text,
                role=role,
                contract=contract,
                location=location,
                sources=sources,
                limit=limit,
                top_k=top_k,
            )
        except Exception as e:
            st.error(
                "La recherche a échoué (timeout ou API lente).\n\n"
                "✅ Vérifie que le serveur MCP tourne ET répond aux appels jobs_list.\n"
                "👉 Test rapide: `curl -s -X POST http://127.0.0.1:8765/rpc -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"jobs_list\",\"arguments\":{\"query\":\"data analyst\",\"location\":\"Paris\",\"limit\":5,\"sources\":[\"adzuna\",\"remotive\"],\"skip_failed_sources\":true}}}'`\n\n"
                f"Erreur: {e}"
            )
            st.stop()

        # ---- Clean UI: show a compact summary, keep meta/trace only in dev mode ----
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        m = meta.get("jobs_list_meta") or {}
        g = meta.get("graph_summary") or {}

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Offres (API)", int(m.get("count_total") or 0))
        with c2:
            st.metric("France", int(m.get("after_country_filter") or 0))
        with c3:
            st.metric("Après filtre contrat", int(m.get("after_title_contract_filter") or 0))
        with c4:
            st.metric("Ranked", int(m.get("ranked_count") or 0))

        st.markdown("<hr class='thin-hr' />", unsafe_allow_html=True)
        st.markdown(
            " ".join(
                [
                    _badge(f"Query: {meta.get('query_used')}", "info"),
                    _badge(f"Strict: {meta.get('strict_filters')}", "info"),
                    _badge(f"Sources: {', '.join(meta.get('sources') or [])}", "info"),
                ]
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='small muted'>Graphe: nodes={g.get('node_count','-')} • edges={g.get('edge_count','-')} • cv_skills={g.get('cv_skill_count','-')} • jobs={g.get('job_count','-')}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if 'debug_mode' in locals() and debug_mode:
            with st.expander("🔧 Détails techniques (debug)", expanded=False):
                st.markdown("#### ✅ Requête envoyée")
                st.code(
                    {
                        "query": meta.get("query_used", build_mcp_query(role, contract, location)),
                        "location_param": location,
                        "contract_requested": contract,
                        "strict_filters": meta.get("strict_filters"),
                    }
                )
                st.markdown("#### 📌 Meta")
                st.json(
                    {
                        "role": meta.get("role"),
                        "contract": meta.get("contract"),
                        "location": meta.get("location"),
                        "strict_filters": meta.get("strict_filters"),
                        "jobs_list_meta": meta.get("jobs_list_meta"),
                        "graph_summary": meta.get("graph_summary"),
                        "fallback_tried": meta.get("fallback_tried"),
                    }
                )

            with st.expander("🧪 Trace MCP (debug)", expanded=False):
                st.json(meta.get("trace", []))

        st.markdown("### ⭐ Résultats")
        if not recos:
            st.warning(
                "Aucune reco exploitable.\n\n"
                "Ca peut venir de:\n"
                "- filtres trop stricts (contrat/role pas présents dans les descriptions)\n"
                "- extraction skills job trop pauvre (peu de keywords reconnus)\n"
            )
        else:
            for idx, r in enumerate(recos, start=1):
                j = r["job"]
                expl = r["explain"]
                score = float(r["score"])

                title = j.get("title") or "Sans titre"
                company = j.get("company") or "?"
                score_base = float(r.get("score_base", score))
                score_bonus = float(r.get("score_bonus", 0.0))
                with st.expander(
                    f"#{idx} — {title} | {company} | score={score:.3f} (base={score_base:.3f} + bonus={score_bonus:.3f})",
                    expanded=(idx == 1),
                ):
                    score_base = float(r.get("score_base", score))
                    score_bonus = float(r.get("score_bonus", 0.0))

                    badges = " ".join(
                        [
                            _badge(f"Score: {score:.3f}", "info"),
                            _badge("Rôle ✅" if j.get("role_hit") else "Rôle ⚠️", "ok" if j.get("role_hit") else "warn"),
                            _badge("Contrat ✅" if j.get("contract_hit") else "Contrat ⚠️", "ok" if j.get("contract_hit") else "warn"),
                            _badge(f"base={score_base:.3f} + bonus={score_bonus:.3f}", "info"),
                        ]
                    )

                    st.markdown(
                        f"""
<div class='card'>
  {_job_card_header(_safe_md(title), _safe_md(company), _safe_md(j.get('location') or '?'))}
  <div style='margin-top:0.35rem'>{badges}</div>
  <div class='small muted' style='margin-top:0.45rem'>{_safe_md(_clip(j.get('description') or '', 420))}</div>
  <div class='job-url' style='margin-top:0.55rem'>🔗 <a href='{_safe_md(str(j.get('url') or ''))}' target='_blank'>Ouvrir l’offre</a></div>
</div>
""",
                        unsafe_allow_html=True,
                    )

                    st.markdown("<hr class='thin-hr' />", unsafe_allow_html=True)
                    st.markdown("**Compétences extraites (job)**")
                    if j.get("skills"):
                        st.markdown(" ".join([_badge(s, "info") for s in (j.get("skills") or [])[:40]]), unsafe_allow_html=True)
                    else:
                        st.caption("Aucune compétence reconnue sur cette annonce.")

                    st.markdown("<hr class='thin-hr' />", unsafe_allow_html=True)
                    st.markdown("**Match vs CV**")
                    ms = expl.get("matched_skills", []) or []
                    mis = expl.get("missing_skills", []) or []
                    cL, cR = st.columns(2)
                    with cL:
                        st.markdown("_Matched_")
                        st.markdown(" ".join([_badge(s, "ok") for s in ms[:40]]) or "—", unsafe_allow_html=True)
                    with cR:
                        st.markdown("_Missing_")
                        st.markdown(" ".join([_badge(s, "warn") for s in mis[:40]]) or "—", unsafe_allow_html=True)

                    st.info(expl.get("why_long") or expl.get("why_short"))

        # Short assistant summary in chat
        summary = f"J’ai compris: **{role}**"
        if contract:
            summary += f" | **{contract.upper()}**"
        summary += f" | **{location}**.\n\n"
        summary += f"Requête MCP: `{meta.get('query_used')}`."
        if meta.get("fallback_tried"):
            summary += f"\nFallbacks: {meta.get('fallback_tried')}"

        st.session_state.messages.append({"role": "assistant", "content": summary})