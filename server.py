"""Run: python3 server.py. Visit http://localhost:8000."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError

from agent import respond

STATIC = Path(__file__).parent / "static"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        if self.path not in files:
            return self.send_error(404)
        filename, content_type = files[self.path]
        data = (STATIC / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 50000:
                raise ValueError("Request body must be 1–50 KB.")
            payload = json.loads(self.rfile.read(length))
            history = payload.get("history")
            if not isinstance(history, list) or not 1 <= len(history) <= 30:
                raise ValueError("Invalid conversation length.")
            if any(not isinstance(turn, dict) or turn.get("role") not in ("user", "assistant") or not isinstance(turn.get("content"), str) or len(turn["content"]) > 2000 for turn in history):
                raise ValueError("Invalid conversation turn.")
            if history[-1]["role"] != "user":
                raise ValueError("Last turn must be from the user.")
            answer, activity, mode = respond(history)
            self.json_response(200, {"answer": answer, "activity": activity, "mode": mode})
        except (ValueError, json.JSONDecodeError) as error:
            self.json_response(400, {"error": str(error)})
        except (HTTPError, URLError, TimeoutError) as error:
            self.json_response(502, {"error": f"Model request failed: {error}"})

    def json_response(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Bookly demo: http://localhost:8000", flush=True)
    server.serve_forever()
