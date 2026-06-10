from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .errors import RpcError
from .protocol import has_id, make_response, validate_request_envelope
from .serialization import deserialize_value, serialize_value
from .validation import SchemaValidator
from .version import __version__


Handler = Callable[..., Any]


@dataclass
class RpcHttpResponse:
    status: int
    headers: dict[str, str]
    body: Any | None = None


@dataclass
class MethodConfig:
    handler: Handler
    schema: dict[str, Any] | None = None
    description: str = ""
    expose_schema: bool = False


class RpcEndpoint:
    def __init__(
        self,
        context: Any = None,
        *,
        safe_enabled: bool = False,
        strict_mode: bool = True,
        enable_introspection: bool = False,
        introspection_prefix: str = "__rpc",
        max_serialization_depth: int = 100,
        max_deserialization_depth: int = 100,
    ):
        self.context = context
        self.methods: dict[str, MethodConfig] = {}
        self.safe_enabled = safe_enabled
        self.strict_mode = strict_mode
        self.enable_introspection = enable_introspection
        self.introspection_prefix = introspection_prefix
        self.max_serialization_depth = max_serialization_depth
        self.max_deserialization_depth = max_deserialization_depth
        self.validator = SchemaValidator()

        if self.enable_introspection:
            self._register_introspection_methods()

    def add_method(
        self,
        name: str,
        handler: Handler,
        *,
        schema: dict[str, Any] | None = None,
        description: str = "",
        expose_schema: bool = False,
    ) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("Method name must be a non-empty string")

        self.methods[name] = MethodConfig(
            handler=handler,
            schema=schema,
            description=description,
            expose_schema=expose_schema,
        )

    def remove_method(self, name: str) -> None:
        self.methods.pop(name, None)

    def list_methods(self) -> list[str]:
        return list(self.methods.keys())

    def handle_request(self, payload: str | bytes | dict[str, Any] | list[Any], context: dict[str, Any] | None = None) -> str:
        response = self.handle_payload(payload, context)
        if response.status == 204 or response.body is None:
            return ""
        return json.dumps(response.body, separators=(",", ":"), default=str)

    def handle_payload(
        self,
        payload: str | bytes | dict[str, Any] | list[Any],
        context: dict[str, Any] | None = None,
    ) -> RpcHttpResponse:
        headers = {
            "content-type": "application/json",
            "x-rpc-safe-enabled": "true" if self.safe_enabled else "false",
        }

        try:
            request = self._decode_payload(payload)
        except Exception as exc:
            return RpcHttpResponse(
                200,
                headers,
                make_response(
                    None,
                    error={
                        "code": -32700,
                        "message": "Parse error",
                        "data": {"message": str(exc)},
                    },
                ),
            )

        request_context = context or {}
        try:
            if isinstance(request, list):
                return self._process_batch(request, request_context, headers)

            result = self._process_single(request, request_context)
            if result is None:
                return RpcHttpResponse(204, headers)

            return RpcHttpResponse(200, headers, result)
        except RpcError as exc:
            return RpcHttpResponse(200, headers, self._make_error_response(None, exc))
        except Exception as exc:
            return RpcHttpResponse(
                200,
                headers,
                self._make_error_response(None, RpcError(str(exc), -32603)),
            )

    def serialize_bigints_and_dates(self, value: Any) -> Any:
        return serialize_value(
            value,
            safe_enabled=self.safe_enabled,
            max_depth=self.max_serialization_depth,
        )

    def deserialize_bigints_and_dates(self, value: Any, *, safe_enabled: bool | None = None) -> Any:
        return deserialize_value(
            value,
            safe_enabled=self.safe_enabled if safe_enabled is None else safe_enabled,
            max_depth=self.max_deserialization_depth,
        )

    def _process_batch(
        self,
        batch: list[Any],
        context: dict[str, Any],
        headers: dict[str, str],
    ) -> RpcHttpResponse:
        if not batch:
            return RpcHttpResponse(
                200,
                headers,
                make_response(None, error={"code": -32600, "message": "Invalid Request"}),
            )

        responses = []
        for item in batch:
            result = self._process_single(item, context)
            if result is not None:
                responses.append(result)

        if not responses:
            return RpcHttpResponse(204, headers)

        return RpcHttpResponse(200, headers, responses)

    def _process_single(self, request: Any, context: dict[str, Any]) -> dict[str, Any] | None:
        try:
            validate_request_envelope(request)
            client_safe_enabled = self._client_safe_enabled(context)

            if self.safe_enabled and self.strict_mode and not self._has_safe_header(context):
                raise RpcError("Safe Mode requires X-RPC-Safe-Enabled header", -32600)

            method_name = request["method"]
            method = self.methods.get(method_name)
            if method is None:
                raise RpcError(f"Method not found: {method_name}", -32601)

            params = request.get("params", {})
            if client_safe_enabled:
                params = self.deserialize_bigints_and_dates(params, safe_enabled=True)

            self.validator.validate(params, method.schema)
            result = self._execute_handler(method.handler, request, context, params)

            if not has_id(request):
                return None

            return make_response(
                request.get("id"),
                result=self.serialize_bigints_and_dates(result),
            )
        except RpcError as exc:
            if isinstance(request, dict) and not has_id(request):
                return None
            request_id = request.get("id") if isinstance(request, dict) else None
            return self._make_error_response(request_id, exc)
        except Exception as exc:
            if isinstance(request, dict) and not has_id(request):
                return None
            request_id = request.get("id") if isinstance(request, dict) else None
            return self._make_error_response(request_id, RpcError(str(exc), -32603))

    def _make_error_response(self, request_id: Any, error: RpcError) -> dict[str, Any]:
        body = {
            "code": error.code,
            "message": str(error),
        }

        if error.data is not None:
            body["data"] = self.serialize_bigints_and_dates(error.data)

        return make_response(request_id, error=body)

    def _execute_handler(
        self,
        handler: Handler,
        request: dict[str, Any],
        context: dict[str, Any],
        params: Any,
    ) -> Any:
        result = handler(request, self.context if self.context is not None else context, params)
        if inspect.isawaitable(result):
            raise RpcError("Async handlers require an async adapter", -32603)
        return result

    def _register_introspection_methods(self) -> None:
        prefix = self.introspection_prefix

        self.add_method(
            f"{prefix}.listMethods",
            lambda _request, _context, _params: [
                name for name in self.methods if not name.startswith(f"{prefix}.")
            ],
        )
        self.add_method(
            f"{prefix}.version",
            lambda _request, _context, _params: {
                "toolkit": "rpc-python-toolkit",
                "version": __version__,
                "methodCount": len(
                    [name for name in self.methods if not name.startswith(f"{prefix}.")]
                ),
            },
        )
        self.add_method(f"{prefix}.describe", self._describe_method)
        self.add_method(
            f"{prefix}.capabilities",
            lambda _request, _context, _params: {
                "jsonrpc": "2.0",
                "batch": True,
                "notifications": True,
                "introspection": True,
                "safeMode": self.safe_enabled,
                "transport": "python-http",
            },
        )

    def _describe_method(self, _request: dict[str, Any], _context: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict) or not isinstance(params.get("method"), str):
            raise RpcError("Invalid params: method name required", -32602)

        method_name = params["method"]
        if method_name.startswith(f"{self.introspection_prefix}."):
            raise RpcError("Cannot describe introspection methods", -32601)

        method = self.methods.get(method_name)
        if method is None:
            raise RpcError(f"Method not found: {method_name}", -32601)

        return {
            "name": method_name,
            "description": method.description,
            "schema": method.schema if method.expose_schema else None,
        }

    @staticmethod
    def _decode_payload(payload: str | bytes | dict[str, Any] | list[Any]) -> Any:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        if isinstance(payload, str):
            return json.loads(payload)

        return payload

    @staticmethod
    def _normalized_headers(context: dict[str, Any]) -> dict[str, str]:
        headers = context.get("headers", {}) or {}
        return {str(key).lower(): str(value) for key, value in headers.items()}

    def _has_safe_header(self, context: dict[str, Any]) -> bool:
        headers = self._normalized_headers(context)
        return "x-rpc-safe-enabled" in headers or "x-rpc-safe" in headers

    def _client_safe_enabled(self, context: dict[str, Any]) -> bool:
        headers = self._normalized_headers(context)
        value = headers.get("x-rpc-safe-enabled", headers.get("x-rpc-safe"))
        return str(value).lower() == "true"


class RpcSafeEndpoint(RpcEndpoint):
    def __init__(self, context: Any = None, **options: Any):
        options.setdefault("safe_enabled", True)
        options.setdefault("strict_mode", True)
        super().__init__(context, **options)

