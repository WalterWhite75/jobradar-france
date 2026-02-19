import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from server.mcp.tools import tools_list, tool_call
from server.mcp.resources import resource_read

class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/rpc":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            req = json.loads(raw)
            method = req.get("method")
            params = req.get("params", {}) or {}
            rid = req.get("id")

            if method == "initialize":
                result = {"name": "mcp_job_matcher", "version": "0.1"}
            elif method == "tools/list":
                result = tools_list()
            elif method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments", {}) or {}
                result = tool_call(name, arguments)
            elif method == "resources/read":
                uri = params.get("uri")
                arguments = params.get("arguments", {}) or {}
                result = resource_read(uri, arguments)
            else:
                raise ValueError(f"Unknown method: {method}")

            self._send(200, {"jsonrpc": "2.0", "id": rid, "result": result})

        except Exception as e:
            self._send(200, {"jsonrpc": "2.0", "id": None, "error": {"message": str(e)}})

def main(host="127.0.0.1", port=8765):
    print(f"[MCP] HTTP JSON-RPC listening on http://{host}:{port}/rpc")
    HTTPServer((host, port), Handler).serve_forever()

if __name__ == "__main__":
    main()