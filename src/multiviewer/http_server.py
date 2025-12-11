from __future__ import annotations

# Standard library
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

from . import aio

# Local package
from .base import *

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8787


class Server(ThreadingHTTPServer):
    # This must be a class attribute, not an instance attribute, in order to
    # affect socket creation, which happens before init.
    allow_reuse_address = True

    stop: bool

    run_command: Callable[[list[str]], Awaitable[JSON]]

    def __init__(self, server_address, request_handler_class, run_command):
        super().__init__(server_address, request_handler_class)
        self.run_command = run_command
        self.stop = False
        self.timeout = 0.1


class RequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return

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
            command_json = json.loads(raw.decode())["command"]
            if not isinstance(command_json, str):
                raise TypeError("command must be a string")
            command = command_json
        except Exception as e:
            log_exc(e)
            self.respond(400, "bad request")
            return
        try:
            response = aio.run_coroutine_threadsafe(
                cast(Server, self.server).run_command(command.split())
            )
            self.respond(200, response)
        except Exception as e:
            log_exc(e)
            self.respond(400, {})


def serve_until_stopped(run_command):
    if False:
        debug_print(run_command)
    server = Server((HTTP_HOST, HTTP_PORT), RequestHandler, run_command)
    log(f"HTTP server listening on {HTTP_HOST}:{HTTP_PORT}")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def stop(server):
    server.shutdown()
    server.server_close()
