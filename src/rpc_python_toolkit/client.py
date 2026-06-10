from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .errors import RpcError, RpcRemoteError
from .serialization import deserialize_value, serialize_value


class RpcClient:
    def __init__(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
        safe_enabled: bool = False,
        require_safe_header: bool = True,
    ):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self.safe_enabled = safe_enabled
        self.require_safe_header = require_safe_header
        self._next_id = 1

    def call(self, method: str, params: Any = None, *, request_id: Any = None) -> Any:
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._make_id() if request_id is None else request_id,
        }
        if params is not None:
            request["params"] = self._encode(params)

        response = self._send(request, expect_response=True)
        if "error" in response:
            error = response["error"]
            data = self._decode(error.get("data"), response.get("_safe_enabled", False))
            raise RpcRemoteError(error.get("message", "RPC error"), error.get("code", -32603), data)

        return self._decode(response.get("result"), response.get("_safe_enabled", False))

    def notify(self, method: str, params: Any = None) -> None:
        request = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            request["params"] = self._encode(params)
        self._send(request, expect_response=False)

    def batch(self, requests: list[dict[str, Any]]) -> list[Any]:
        payload = []
        for item in requests:
            request = {
                "jsonrpc": "2.0",
                "method": item["method"],
            }
            if "id" in item:
                request["id"] = item["id"]
            else:
                request["id"] = self._make_id()
            if "params" in item:
                request["params"] = self._encode(item["params"])
            payload.append(request)

        response = self._send(payload, expect_response=True)
        responses = response if isinstance(response, list) else [response]
        results = []
        for item in responses:
            if "error" in item:
                error = item["error"]
                data = self._decode(error.get("data"), item.get("_safe_enabled", False))
                raise RpcRemoteError(error.get("message", "RPC error"), error.get("code", -32603), data)
            results.append(self._decode(item.get("result"), item.get("_safe_enabled", False)))
        return results

    def _send(self, payload: Any, *, expect_response: bool) -> Any:
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        headers = {
            "content-type": "application/json",
            **self.headers,
        }

        if self.safe_enabled:
            headers["x-rpc-safe-enabled"] = "true"
        else:
            headers.setdefault("x-rpc-safe-enabled", "false")

        request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
                server_safe_header = response.headers.get("X-RPC-Safe-Enabled")
                status = response.status
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8")
            server_safe_header = exc.headers.get("X-RPC-Safe-Enabled")
            status = exc.code

        if status == 204 or response_body == "":
            return [] if not expect_response else {}

        if self.safe_enabled and self.require_safe_header and server_safe_header is None:
            raise RpcError(
                "RPC Compatibility Error: safe client expected X-RPC-Safe-Enabled response header",
                -32603,
            )

        server_safe_enabled = str(server_safe_header).lower() == "true"
        decoded = json.loads(response_body)
        self._attach_safe_flag(decoded, server_safe_enabled)
        return decoded

    def _encode(self, value: Any) -> Any:
        return serialize_value(value, safe_enabled=self.safe_enabled)

    @staticmethod
    def _decode(value: Any, safe_enabled: bool) -> Any:
        return deserialize_value(value, safe_enabled=safe_enabled)

    def _make_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    @staticmethod
    def _attach_safe_flag(value: Any, safe_enabled: bool) -> None:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    item["_safe_enabled"] = safe_enabled
        elif isinstance(value, dict):
            value["_safe_enabled"] = safe_enabled


class RpcSafeClient(RpcClient):
    def __init__(self, url: str, **options: Any):
        options.setdefault("safe_enabled", True)
        options.setdefault("require_safe_header", True)
        super().__init__(url, **options)

