from __future__ import annotations
from typing import Any, Dict, List
import networkx as nx

def build_skill_job_graph(cv_skills: List[str], jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a bipartite graph:
      - Skill nodes: "skill:<name>"
      - Job nodes:   "job:<job_id>"
      - Edge between skill and job if job_skills contains skill
    Input jobs format expected (minimal):
      { "id": "...", "skills": ["python", "sql", ...] }
    """
    G = nx.Graph()

    # Add skill nodes
    for s in cv_skills or []:
        G.add_node(f"skill:{s}", kind="skill", label=s)

    # Add job nodes + edges
    edge_count = 0
    job_count = 0
    for j in jobs or []:
        job_id = j.get("id")
        if not job_id:
            continue
        job_node = f"job:{job_id}"
        G.add_node(job_node, kind="job", label=j.get("title", ""), source=j.get("source", ""))
        job_count += 1

        jskills = j.get("skills") or []
        for s in jskills:
            s_node = f"skill:{s}"
            # Add skill node even if not in CV: useful for graph context
            if not G.has_node(s_node):
                G.add_node(s_node, kind="skill", label=s)

            G.add_edge(job_node, s_node, weight=1.0)
            edge_count += 1

    return {
        "graph": nx.node_link_data(G),  # JSON-serializable
        "summary": {
            "cv_skill_count": len(cv_skills or []),
            "job_count": job_count,
            "node_count": G.number_of_nodes(),
            "edge_count": edge_count,
        },
    }