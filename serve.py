#!/usr/bin/env python3
"""Static server that tells the browser never to cache -- so a reload always
picks up the newest game.html instead of a stale copy."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control","no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma","no-cache")
        self.send_header("Expires","0")
        super().end_headers()
    def log_message(self,*a): pass
if __name__=="__main__":
    print("serving ~/craps on http://localhost:8777 (no cache)")
    ThreadingHTTPServer(("127.0.0.1",8777), H).serve_forever()
