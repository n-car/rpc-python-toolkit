from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from rpc_python_toolkit import RpcClient, RpcEndpoint


def start_server(endpoint: RpcEndpoint) -> tuple[HTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("content-length", "0"))
            payload = self.rfile.read(length)
            response = endpoint.handle_payload(payload, {"headers": dict(self.headers)})

            self.send_response(response.status)
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.end_headers()

            if response.body is not None:
                self.wfile.write(json.dumps(response.body, separators=(",", ":")).encode("utf-8"))

        def log_message(self, _format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


rpc = RpcEndpoint()
rpc.add_method("test", lambda _request, _context, params: {"ok": True, "params": params})

server, url = start_server(rpc)

try:
    client = RpcClient(url)
    result = client.call("test", {"value": 123})
    print(json.dumps(result, indent=2))
finally:
    server.shutdown()
    server.server_close()
