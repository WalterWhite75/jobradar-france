import json
import urllib.request

URL = "http://127.0.0.1:8765/rpc"

def call(method, params=None, _id=1):
    payload = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

if __name__ == "__main__":
    print("initialize:", call("initialize", {}, 1))
    print("tools/list:", call("tools/list", {}, 2))
    print("resources/read jobs/list:", call("resources/read", {"uri": "jobs/list", "arguments": {"query": "data analyst", "limit": 5}}, 3))