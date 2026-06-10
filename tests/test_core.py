from __future__ import annotations

import datetime as dt
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from rpc_python_toolkit import (
    RpcClient,
    RpcEndpoint,
    RpcRemoteError,
    RpcSafeClient,
    RpcSafeEndpoint,
    deserialize_value,
    serialize_value,
)


class CoreTests(unittest.TestCase):
    def test_handles_standard_json_rpc_call(self):
        rpc = RpcEndpoint()
        rpc.add_method("add", lambda _request, _context, params: params["a"] + params["b"])

        response = rpc.handle_payload(
            {
                "jsonrpc": "2.0",
                "method": "add",
                "params": {"a": 2, "b": 3},
                "id": 1,
            }
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, {"jsonrpc": "2.0", "id": 1, "result": 5})

    def test_returns_no_body_for_notifications(self):
        rpc = RpcEndpoint()
        calls = []
        rpc.add_method("notify", lambda _request, _context, params: calls.append(params))

        response = rpc.handle_payload(
            {
                "jsonrpc": "2.0",
                "method": "notify",
                "params": {"ok": True},
            }
        )

        self.assertEqual(response.status, 204)
        self.assertIsNone(response.body)
        self.assertEqual(calls, [{"ok": True}])

    def test_handles_batch_and_filters_notifications(self):
        rpc = RpcEndpoint()
        rpc.add_method("echo", lambda _request, _context, params: params)

        response = rpc.handle_payload(
            [
                {"jsonrpc": "2.0", "method": "echo", "params": {"value": 1}, "id": "a"},
                {"jsonrpc": "2.0", "method": "echo", "params": {"ignored": True}},
            ]
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.body,
            [{"jsonrpc": "2.0", "id": "a", "result": {"value": 1}}],
        )

    def test_enforces_safe_mode_header_in_strict_mode(self):
        rpc = RpcSafeEndpoint()
        rpc.add_method("echo", lambda _request, _context, params: params)

        response = rpc.handle_payload(
            {
                "jsonrpc": "2.0",
                "method": "echo",
                "params": {"value": "S:test"},
                "id": 1,
            }
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["error"]["code"], -32600)

    def test_decodes_and_encodes_safe_mode_values(self):
        rpc = RpcSafeEndpoint()
        rpc.add_method("echo", lambda _request, _context, params: params)

        response = rpc.handle_payload(
            {
                "jsonrpc": "2.0",
                "method": "echo",
                "params": {
                    "value": "S:test",
                    "literal": "S:S:test",
                    "big": "12345678901234567890n",
                },
                "id": 1,
            },
            {"headers": {"x-rpc-safe-enabled": "true"}},
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.body["result"],
            {
                "value": "S:test",
                "literal": "S:S:test",
                "big": "12345678901234567890n",
            },
        )

    def test_serializes_datetimes_and_large_ints(self):
        now = dt.datetime(2026, 6, 11, 10, 30, tzinfo=dt.timezone.utc)

        encoded = serialize_value(
            {
                "text": "S:literal",
                "date": now,
                "big": 9007199254740993,
            },
            safe_enabled=True,
        )

        self.assertEqual(encoded["text"], "S:S:literal")
        self.assertEqual(encoded["date"], "D:2026-06-11T10:30:00+00:00")
        self.assertEqual(encoded["big"], "9007199254740993n")

        decoded = deserialize_value(encoded, safe_enabled=True)
        self.assertEqual(decoded["text"], "S:literal")
        self.assertIsInstance(decoded["date"], dt.datetime)
        self.assertEqual(decoded["big"], 9007199254740993)

    def test_exposes_introspection_methods(self):
        rpc = RpcEndpoint(enable_introspection=True)
        rpc.add_method(
            "ping",
            lambda _request, _context, _params: "pong",
            description="Return pong",
            schema={"type": "object"},
            expose_schema=True,
        )

        version = rpc.handle_payload({"jsonrpc": "2.0", "method": "__rpc.version", "id": 1})
        describe = rpc.handle_payload(
            {
                "jsonrpc": "2.0",
                "method": "__rpc.describe",
                "params": {"method": "ping"},
                "id": 2,
            }
        )
        capabilities = rpc.handle_payload(
            {"jsonrpc": "2.0", "method": "__rpc.capabilities", "id": 3}
        )

        self.assertEqual(version.body["result"]["toolkit"], "rpc-python-toolkit")
        self.assertEqual(describe.body["result"]["name"], "ping")
        self.assertTrue(capabilities.body["result"]["batch"])

    def test_validates_params_against_schema(self):
        rpc = RpcEndpoint()
        rpc.add_method(
            "add",
            lambda _request, _context, params: params["a"] + params["b"],
            schema={
                "type": "object",
                "required": ["a", "b"],
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "additionalProperties": False,
            },
        )

        response = rpc.handle_payload(
            {
                "jsonrpc": "2.0",
                "method": "add",
                "params": {"a": 1},
                "id": 1,
            }
        )

        self.assertEqual(response.body["error"]["code"], -32602)

    def test_http_client_calls_endpoint(self):
        rpc = RpcEndpoint()
        rpc.add_method("test", lambda _request, _context, params: {"ok": True, "params": params})
        server, url = _start_server(rpc)

        try:
            client = RpcClient(url)
            result = client.call("test", {"value": 123})
            self.assertEqual(result, {"ok": True, "params": {"value": 123}})
        finally:
            server.shutdown()
            server.server_close()

    def test_safe_http_client_calls_safe_endpoint(self):
        rpc = RpcSafeEndpoint()
        rpc.add_method("echo", lambda _request, _context, params: params)
        server, url = _start_server(rpc)

        try:
            client = RpcSafeClient(url)
            result = client.call(
                "echo",
                {
                    "value": "S:literal",
                    "big": 9007199254740993,
                },
            )
            self.assertEqual(result, {"value": "S:literal", "big": 9007199254740993})
        finally:
            server.shutdown()
            server.server_close()

    def test_safe_http_client_batch_preserves_notifications(self):
        rpc = RpcSafeEndpoint()
        rpc.add_method("ping", lambda _request, _context, _params: "pong")
        rpc.add_method("notify.record", lambda _request, _context, _params: {"recorded": True})
        server, url = _start_server(rpc)

        try:
            client = RpcSafeClient(url)
            mixed = client.batch(
                [
                    {"method": "ping", "id": 1},
                    {"method": "notify.record", "params": {"event": "batch-notify"}},
                ]
            )
            self.assertEqual(mixed, ["pong"])

            notification_only = client.batch(
                [
                    {"method": "notify.record", "params": {"event": "notification-only"}},
                ]
            )
            self.assertEqual(notification_only, [])
        finally:
            server.shutdown()
            server.server_close()

    def test_client_raises_remote_errors_with_data(self):
        rpc = RpcEndpoint()

        def fail(_request, _context, _params):
            from rpc_python_toolkit import RpcError

            raise RpcError("Domain failure", -32042, {"reason": "bad"})

        rpc.add_method("fail", fail)
        server, url = _start_server(rpc)

        try:
            client = RpcClient(url)
            with self.assertRaises(RpcRemoteError) as raised:
                client.call("fail", {})
            self.assertEqual(raised.exception.code, -32042)
            self.assertEqual(raised.exception.data, {"reason": "bad"})
        finally:
            server.shutdown()
            server.server_close()


def _start_server(endpoint: RpcEndpoint) -> tuple[HTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("content-length", "0"))
            payload = self.rfile.read(length)
            response = endpoint.handle_payload(
                payload,
                {"headers": dict(self.headers)},
            )

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


if __name__ == "__main__":
    unittest.main()
