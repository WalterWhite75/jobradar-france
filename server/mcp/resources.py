from typing import Any, Dict
from server.mcp.tools import tool_call

def resource_read(uri: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal resources:
      - jobs/list -> same as jobs_list tool (for demo)
    """
    if uri == "jobs/list":
        query = params.get("query", "")
        limit = int(params.get("limit", 10))
        return tool_call("jobs_list", {"query": query, "limit": limit})

    raise ValueError(f"Unknown resource uri: {uri}")