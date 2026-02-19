import re
from typing import List, Dict, Any, Set, Tuple

# Goal: extract ONLY technical skills (tools/tech), with lightweight alias normalization
# so that CV skills overlap job skills.

# ---- 1) Allowlist (technical-only) ----
# Keep this list focused on technologies, tools, platforms, and libraries.
SKILL_KEYWORDS: List[str] = [
    # Languages
    "python", "sql", "r", "java", "javascript", "scala",

    # BI / Data viz tools
    "power bi", "powerbi", "tableau",

    # Databases
    "sql server", "postgresql", "postgres", "mysql",

    # Data / ML libs
    "pandas", "numpy", "scikit-learn", "sklearn", "scikit learn",

    # Data engineering / infra
    "etl", "datawarehouse", "data warehouse", "data pipeline",
    "spark", "hadoop", "airflow", "dbt",

    # Cloud
    "aws", "azure", "gcp", "bigquery", "snowflake",

    # Containers / orchestration
    "docker", "kubernetes",

    # Dev / ops
    "git", "linux", "bash", "api", "rest", "json",
    "ci/cd", "cicd", "devops",
]

# ---- 2) Aliases -> canonical skill ----
# IMPORTANT: keep canonical values stable across CV + job extraction.
NORMALIZE_MAP: Dict[str, str] = {
    # sklearn
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",

    # data warehouse
    "data warehouse": "datawarehouse",

    # power bi family
    "powerbi": "power bi",

    # common BI wording in job descriptions -> power bi (so it overlaps with CV 'power bi')
    "business intelligence": "power bi",
    "reporting": "power bi",
    "dashboard": "power bi",
    "dashboards": "power bi",
    "dashboarding": "power bi",
    "tableau de bord": "power bi",
    "tableaux de bord": "power bi",
    "dataviz": "power bi",
    "data viz": "power bi",
    "data visualisation": "power bi",
    "visualisation": "power bi",

    # ETL wording
    "data pipeline": "etl",

    # SQL family -> sql (single canonical bucket)
    "sql server": "sql",
    "postgresql": "sql",
    "postgres": "sql",
    "mysql": "sql",

    # DevOps
    "ci/cd": "devops",
    "cicd": "devops",
}

# ---- 3) Stop terms (non-technical) ----
# Prevent role/soft-skill terms from ever becoming "skills" even if later added by mistake.
STOP_TERMS: Set[str] = {
    "data analyst",
    "data scientist",
    "data engineer",
    "business analyst",
    "data analysis",
    "analytics",
    "analyste",
    "analyst",
    "stage",
    "intern",
    "internship",
    "alternance",
    "apprentissage",
    "cdi",
    "cdd",
}


def _normalize_skill(s: str) -> str:
    """Normalize a matched keyword into a canonical technical skill."""
    s = (s or "").strip().lower()
    # normalize separators to spaces
    s = re.sub(r"[\s\-_\/]+", " ", s)
    s = NORMALIZE_MAP.get(s, s)
    return s


def _compile_patterns(keywords: List[str]) -> List[Tuple[str, re.Pattern]]:
    """Compile robust regex patterns.

    - Single token: \bpython\b
    - Multi-word: "power bi" -> \bpower[\s\-_/]+bi\b
    """
    patterns: List[Tuple[str, re.Pattern]] = []
    for kw in keywords:
        k = (kw or "").strip().lower()
        if not k:
            continue

        if " " in k:
            parts = [re.escape(p) for p in k.split() if p]
            expr = r"\b" + r"[\s\-_\/]+".join(parts) + r"\b"
            pat = re.compile(expr, flags=re.IGNORECASE)
        else:
            pat = re.compile(r"\b" + re.escape(k) + r"\b", flags=re.IGNORECASE)

        patterns.append((k, pat))
    return patterns


_COMPILED_PATTERNS = _compile_patterns(SKILL_KEYWORDS)


def extract_skills(text: str) -> List[str]:
    """MVP extraction: allowlist dictionary + regex + light alias normalization."""
    if not text:
        return []

    found: Set[str] = set()

    # 1) regex matches from allowlist
    for kw, pat in _COMPILED_PATTERNS:
        if pat.search(text):
            canon = _normalize_skill(kw)
            if canon and canon not in STOP_TERMS:
                found.add(canon)

    # 2) handle common glued variants that word boundaries may miss
    t = text.lower()

    # PowerBI (glued)
    if "powerbi" in t:
        found.add("power bi")

    # SQLServer (glued)
    if "sqlserver" in t or "ms sql" in t or "mssql" in t:
        found.add("sql")

    # Postgres variants
    if "postgresql" in t or re.search(r"\bpostgre\s*sql\b", t):
        found.add("sql")

    # Remove any accidental non-tech items
    found = {s for s in found if s and s not in STOP_TERMS}

    return sorted(found)


def extract_skills_with_meta(text: str) -> Dict[str, Any]:
    skills = extract_skills(text)
    return {
        "skills": skills,
        "method": "keyword_dictionary_mvp",
        "count": len(skills),
    }