from __future__ import annotations

# Standard library
import json
import threading

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Local package
from .base import *
from . import aio

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8787

class Server(ThreadingHTTPServer):
    # This must be a class attribute, not an instance attribute, in order to 
    # affect socket creation, which happens before init.
    allow_reuse_address = True

    stop: bool

    run_command: Callable[[list[str]], Awaitable[JSON]]
    
    def __init__(self, server_address, RequestHandlerClass, run_command):
        super().__init__(server_address, RequestHandlerClass)
        self.run_command = run_command
        self.stop = False
        self.timeout = 0.1

class RequestHandler(SimpleHTTPRequestHandler):
    server: Server

    def log_message(self, fmt, *args): return

    def respond(self, code: int, j: JSON):
        body = (json.dumps(j) + "\n").encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.respond(200, {})

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            command = json.loads(raw.decode())["command"]
        except Exception as e:
            log_exc(e)
            self.respond(400, f"bad request")
            return
        try:
            response = aio.run_coroutine_threadsafe(
                self.server.run_command(command.split()))
            self.respond(200, response)
        except Exception as e:
            log_exc(e)
            self.respond(400, {})

def serve_until_stopped(run_command):
    if False: debug_print(run_command)
    server = Server((HTTP_HOST, HTTP_PORT), RequestHandler, run_command)
    log(f"HTTP server listening on {HTTP_HOST}:{HTTP_PORT}")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

def stop(server):
    server.shutdown()
    server.server_close()