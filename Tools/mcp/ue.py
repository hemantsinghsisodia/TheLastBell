"""Unreal MCP helper for agents (editor must be open; server at http://127.0.0.1:8000/mcp).

CLI:
    python ue.py describe <toolset> [tool]          # list tools, or one tool's schema
    python ue.py <toolset> <tool> '<json-args>'     # call a tool, print the result
Library:
    from ue import UE; ue = UE(); ue.call(toolset, tool, args)
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8000/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


class UE:
    def __init__(self, url=URL):
        self.url, self.sid, self.n = url, None, 0
        self._post({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "lastbell", "version": "0"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _post(self, body):
        h = dict(HEADERS)
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, json.dumps(body).encode(), h)
        with urllib.request.urlopen(req, timeout=600) as r:
            self.sid = self.sid or r.headers.get("Mcp-Session-Id")
            raw = r.read().decode("utf-8", "replace").strip()
        if not raw:
            return None
        if not raw.startswith("{"):
            raw = next(line[5:] for line in raw.splitlines() if line.startswith("data:"))
        return json.loads(raw)

    def raw(self, name, arguments):
        self.n += 1
        res = self._post({"jsonrpc": "2.0", "id": self.n, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments}})
        if "error" in res:
            raise RuntimeError(res["error"])
        text = "".join(c.get("text", "") for c in res["result"].get("content", []))
        if res["result"].get("isError"):
            raise RuntimeError(text)
        try:
            return json.loads(text)
        except Exception:
            return text

    def call(self, toolset, tool, args=None):
        r = self.raw("call_tool", {"toolset_name": toolset, "tool_name": tool, "arguments": args or {}})
        if isinstance(r, str) and ("is required" in r or "rror" in r[:200]):
            raise RuntimeError(r[:1500])
        return r["returnValue"] if isinstance(r, dict) and "returnValue" in r else r

    def describe(self, toolset):
        return self.raw("describe_toolset", {"toolset_name": toolset})


if __name__ == "__main__":
    ue = UE()
    if sys.argv[1] == "describe":
        d = ue.describe(sys.argv[2])
        only = sys.argv[3] if len(sys.argv) > 3 else None
        for t in d["tools"]:
            short = t["name"].split(".")[-1]
            if only and short != only:
                continue
            print("-", short, ":", (t.get("description") or "")[:300 if only else 110].replace("\n", " "))
            if only:
                print(json.dumps(t["inputSchema"])[:3000])
    else:
        out = ue.call(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
        print(json.dumps(out, indent=1) if not isinstance(out, str) else out)
