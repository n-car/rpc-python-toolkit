from __future__ import annotations

import unittest

from rpc_python_toolkit import RpcEndpoint, RpcSafeEndpoint


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.rpc = RpcEndpoint()
        self.calls = []
        self.rpc.add_method("echo", self.echo)

    def echo(self, _request, _context, params):
        self.calls.append(params)
        return params

    def test_invalid_envelopes_are_errors_not_notifications(self):
        for request in [None, 1, True, "echo", {}, {"method": "echo"},
                        {"jsonrpc": "1.0", "method": "echo"},
                        {"jsonrpc": "2.0", "method": True}]:
            with self.subTest(request=request):
                response = self.rpc.handle_payload(request)
                self.assertEqual(response.status, 200)
                # A bare string is decoded as JSON; exercise structured invalid
                # envelopes separately from JSON parse failures.
                expected_code = -32700 if request == "echo" else -32600
                self.assertEqual(response.body["error"]["code"], expected_code)
                self.assertIsNone(response.body["id"])
        self.assertEqual(self.calls, [])

    def test_rejects_invalid_ids_without_echoing_them(self):
        for request_id in [True, False, {}, [], float("nan"), float("inf"), -float("inf")]:
            with self.subTest(request_id=request_id):
                response = self.rpc.handle_payload(
                    {"jsonrpc": "2.0", "method": "echo", "id": request_id}
                )
                self.assertEqual(response.body["error"]["code"], -32600)
                self.assertIsNone(response.body["id"])
        self.assertEqual(self.calls, [])

    def test_non_json_constants_on_wire_are_parse_errors(self):
        for token in ["NaN", "Infinity", "-Infinity"]:
            for member in ['"params":{"value":' + token + '}', '"id":' + token]:
                with self.subTest(token=token, member=member):
                    response = self.rpc.handle_payload(
                        '{"jsonrpc":"2.0","method":"echo",' + member + '}'
                    )
                    self.assertEqual(response.body,
                                     {"jsonrpc": "2.0", "id": None,
                                      "error": {"code": -32700, "message": "Parse error"}})
        self.assertEqual(self.calls, [])

    def test_valid_json_number_overflow_in_id_is_invalid_request(self):
        response = self.rpc.handle_payload('{"jsonrpc":"2.0","method":"echo","id":1e999}')
        self.assertEqual(response.body["error"]["code"], -32600)
        self.assertIsNone(response.body["id"])
        self.assertEqual(self.calls, [])

    def test_explicit_null_and_other_valid_ids_receive_responses(self):
        for request_id in [None, 0, 1.5, "", "S:literal", "D:2026-01-01", "123n"]:
            with self.subTest(request_id=request_id):
                response = self.rpc.handle_payload(
                    {"jsonrpc": "2.0", "method": "echo", "params": {}, "id": request_id}
                )
                self.assertEqual(response.body, {"jsonrpc": "2.0", "id": request_id, "result": {}})

    def test_params_must_be_object_or_array_when_present(self):
        for params in [None, True, 1, "text"]:
            for with_id in [True, False]:
                with self.subTest(params=params, with_id=with_id):
                    request = {"jsonrpc": "2.0", "method": "echo", "params": params}
                    if with_id:
                        request["id"] = 7
                    response = self.rpc.handle_payload(request)
                    self.assertEqual(response.body["error"]["code"], -32600)
                    self.assertIsNone(response.body["id"])
        self.assertEqual(self.calls, [])

    def test_mixed_batch_retains_invalid_elements_and_explicit_null_calls(self):
        response = self.rpc.handle_payload([
            {},
            {"jsonrpc": "2.0", "method": "echo"},
            {"jsonrpc": "2.0", "method": "echo", "params": [], "id": None},
            {"jsonrpc": "2.0", "method": "missing"},
        ])
        self.assertEqual(len(response.body), 2)
        self.assertEqual(response.body[0]["error"]["code"], -32600)
        self.assertEqual(response.body[1], {"jsonrpc": "2.0", "id": None, "result": []})

    def test_all_valid_notifications_have_no_response(self):
        response = self.rpc.handle_payload([
            {"jsonrpc": "2.0", "method": "echo"},
            {"jsonrpc": "2.0", "method": "missing"},
        ])
        self.assertEqual(response.status, 204)
        self.assertIsNone(response.body)

    def test_safe_mode_keeps_envelope_literals_and_nested_empty_containers(self):
        rpc = RpcSafeEndpoint()
        rpc.add_method("S:echo", self.echo)
        response = rpc.handle_payload(
            {"jsonrpc": "2.0", "method": "S:echo", "params": {"object": {}, "array": []}, "id": "123n"},
            {"headers": {"x-rpc-safe-enabled": "true"}},
        )
        self.assertEqual(response.body,
                         {"jsonrpc": "2.0", "id": "123n", "result": {"object": {}, "array": []}})


if __name__ == "__main__":
    unittest.main()
