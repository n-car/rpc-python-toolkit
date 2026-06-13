from __future__ import annotations

import datetime as dt
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from rpc_python_toolkit import RpcSafeClient, RpcSafeEndpoint


def start_server(endpoint: RpcSafeEndpoint) -> tuple[HTTPServer, str]:
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
                self.wfile.write(
                    json.dumps(response.body, separators=(",", ":"), default=str).encode("utf-8")
                )

        def log_message(self, _format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


rpc = RpcSafeEndpoint()


def echo_types(_request, _context, params):
    return {
        "received": {
            "text": params["text"],
            "marker_string": params["marker_string"],
            "when_type": type(params["when"]).__name__,
            "when": params["when"],
            "big_type": type(params["big"]).__name__,
            "big": params["big"],
        },
        "server_values": {
            "marker_string": "S:server-literal",
            "when": dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc),
            "big": 9007199254740993,
        },
    }


rpc.add_method("types.echo", echo_types)

server, url = start_server(rpc)

try:
    client = RpcSafeClient(url)
    result = client.call(
        "types.echo",
        {
            "text": "plain string",
            "marker_string": "S:client-literal",
            "when": dt.datetime(2026, 6, 13, 8, 30, tzinfo=dt.timezone.utc),
            "big": 9007199254740993,
        },
    )
    print(json.dumps(result, indent=2, default=str))
finally:
    server.shutdown()
    server.server_close()
