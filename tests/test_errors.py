from __future__ import annotations

import unittest
from unittest.mock import patch

from rpc_python_toolkit import RpcEndpoint, RpcError, RpcSafeEndpoint


class ErrorSanitizationTests(unittest.TestCase):
    def test_unexpected_handler_error_is_generic_even_with_code_and_data(self):
        rpc = RpcEndpoint()
        failure = RuntimeError("Synthetic private configuration detail")
        failure.code = -32042
        failure.data = {"path": "/private/example/config.ini"}

        def fail(_request, _context, _params):
            raise failure

        rpc.add_method("fail", fail)

        response = rpc.handle_payload({"jsonrpc": "2.0", "method": "fail", "id": 1})

        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.body,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32603, "message": "Internal error"},
            },
        )

    def test_explicit_internal_error_also_hides_message_and_data(self):
        rpc = RpcEndpoint()

        def fail(_request, _context, _params):
            raise RpcError("Synthetic database detail", -32603, {"path": "/private/example"})

        rpc.add_method("fail", fail)

        response = rpc.handle_payload({"jsonrpc": "2.0", "method": "fail", "id": 2})

        self.assertEqual(response.body["error"], {"code": -32603, "message": "Internal error"})

    def test_explicit_application_error_preserves_code_message_and_data(self):
        rpc = RpcEndpoint()

        def fail(_request, _context, _params):
            raise RpcError("Quota exceeded", -32042, {"limit": 10})

        rpc.add_method("fail", fail)

        response = rpc.handle_payload({"jsonrpc": "2.0", "method": "fail", "id": 3})

        self.assertEqual(
            response.body["error"],
            {"code": -32042, "message": "Quota exceeded", "data": {"limit": 10}},
        )

    def test_batch_sanitizes_errors_without_responding_to_failed_notifications(self):
        rpc = RpcEndpoint()

        def fail(_request, _context, _params):
            raise RuntimeError("Synthetic batch detail")

        rpc.add_method("fail", fail)
        rpc.add_method("echo", lambda _request, _context, params: params)

        response = rpc.handle_payload(
            [
                {"jsonrpc": "2.0", "method": "fail", "id": 1},
                {"jsonrpc": "2.0", "method": "fail"},
                {"jsonrpc": "2.0", "method": "echo", "params": [1, 2], "id": 2},
            ]
        )

        self.assertEqual(
            response.body,
            [
                {"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "Internal error"}},
                {"jsonrpc": "2.0", "id": 2, "result": [1, 2]},
            ],
        )

    def test_unexpected_outer_error_is_sanitized(self):
        rpc = RpcEndpoint()

        with patch.object(rpc, "_process_batch", side_effect=RuntimeError("Synthetic adapter detail")):
            response = rpc.handle_payload([{"jsonrpc": "2.0", "method": "echo", "id": 1}])

        self.assertEqual(
            response.body,
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": "Internal error"}},
        )

    def test_unexpected_validation_error_is_sanitized(self):
        rpc = RpcEndpoint()
        rpc.add_method("echo", lambda _request, _context, params: params)

        with patch.object(rpc.validator, "validate", side_effect=RuntimeError("Synthetic validator detail")):
            response = rpc.handle_payload({"jsonrpc": "2.0", "method": "echo", "id": 1})

        self.assertEqual(response.body["error"], {"code": -32603, "message": "Internal error"})

    def test_parse_error_omits_diagnostic_data_by_default(self):
        response = RpcEndpoint().handle_payload("{")

        self.assertEqual(response.body["error"], {"code": -32700, "message": "Parse error"})

        debug_response = RpcEndpoint(sanitize_errors=False).handle_payload("{")
        self.assertEqual(debug_response.body["error"]["code"], -32700)
        self.assertTrue(debug_response.body["error"]["data"]["message"])

    def test_debug_option_preserves_internal_details(self):
        for failure, expected in [
            (RuntimeError("Synthetic debug detail"), {"code": -32603, "message": "Synthetic debug detail"}),
            (
                RpcError("Synthetic debug detail", -32603, {"path": "/private/example"}),
                {"code": -32603, "message": "Synthetic debug detail", "data": {"path": "/private/example"}},
            ),
        ]:
            with self.subTest(error_type=type(failure).__name__):
                rpc = RpcEndpoint(sanitize_errors=False)

                def fail(_request, _context, _params):
                    raise failure

                rpc.add_method("fail", fail)
                response = rpc.handle_payload({"jsonrpc": "2.0", "method": "fail", "id": 1})

                self.assertEqual(response.body["error"], expected)

    def test_safe_mode_preserves_application_data_and_sanitizes_internal_errors(self):
        rpc = RpcSafeEndpoint()

        def fail(_request, _context, params):
            if params["internal"]:
                raise RuntimeError("Synthetic Safe Mode detail")
            raise RpcError("Quota exceeded", -32042, {"reason": "limit"})

        rpc.add_method("fail", fail)

        response = rpc.handle_payload(
            [
                {"jsonrpc": "2.0", "method": "fail", "params": {"internal": False}, "id": 1},
                {"jsonrpc": "2.0", "method": "fail", "params": {"internal": True}, "id": 2},
            ],
            {"headers": {"x-rpc-safe-enabled": "true"}},
        )

        self.assertEqual(
            response.body[0]["error"],
            {"code": -32042, "message": "Quota exceeded", "data": {"reason": "S:limit"}},
        )
        self.assertEqual(response.body[1]["error"], {"code": -32603, "message": "Internal error"})


if __name__ == "__main__":
    unittest.main()
