from __future__ import annotations
from typing import Any, Dict, List, Optional

def explain_match(
    cv_skills: List[str],
    job_skills: List[str],
    job: Optional[Dict[str, Any]] = None,
    score: Optional[float] = None,
    top_n: int = 6,
) -> Dict[str, Any]:
    """
    Produce an explanation based on skill overlap (graph-based reasoning).
    No rules-based scoring. Purely: matched vs missing skills.

    Returns:
      - matched_skills
      - missing_skills
      - coverage (ratio)
      - why_short / why_long
    """
    cv = [s.strip().lower() for s in (cv_skills or []) if str(s).strip()]
    js = [s.strip().lower() for s in (job_skills or []) if str(s).strip()]

    cv_set = set(cv)
    js_set = set(js)

    matched = sorted(cv_set.intersection(js_set))
    missing = sorted(js_set.difference(cv_set))

    coverage = (len(matched) / len(cv_set)) if cv_set else 0.0
    if score is None:
        score = coverage

    # Small helper for friendly text
    title = (job or {}).get("title") if job else None
    company = (job or {}).get("company") if job else None

    matched_disp = matched[:top_n]
    missing_disp = missing[:top_n]

    if title and company:
        header = f"{title} — {company}"
    elif title:
        header = title
    else:
        header = "Offre"

    why_short = (
        f"{header}: couverture {round(score*100)}% "
        f"({len(matched)}/{len(cv_set) if cv_set else 0} compétences du CV matchées)."
    )

    # Build a longer justification
    lines = []
    if matched_disp:
        lines.append("Points forts (compétences matchées) : " + ", ".join(matched_disp) + ".")
    else:
        lines.append("Aucune compétence du CV n’a été reconnue dans cette offre (matching faible).")

    if missing_disp:
        lines.append("Compétences manquantes / à renforcer : " + ", ".join(missing_disp) + ".")
    else:
        lines.append("Aucune compétence manquante majeure détectée (sur la liste extraite).")

    lines.append(
        "Interprétation : le score provient d’un raisonnement graphe (connectivité skills↔job), "
        "pas d’un ensemble de règles arbitraires."
    )

    why_long = " ".join(lines)

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "coverage": round(coverage, 6),
        "score": round(float(score), 6),
        "why_short": why_short,
        "why_long": why_long,
    }