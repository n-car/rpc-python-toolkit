from __future__ import annotations

import math
from typing import Any

from .errors import RpcError


def has_id(request: dict[str, Any]) -> bool:
    return "id" in request


def make_response(
    request_id: Any,
    *,
    result: Any = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def validate_request_envelope(request: Any) -> None:
    if not isinstance(request, dict):
        raise RpcError("Invalid Request", -32600)

    if request.get("jsonrpc") != "2.0":
        raise RpcError("Invalid JSON-RPC version", -32600)

    method = request.get("method")
    if not isinstance(method, str) or not method:
        raise RpcError("Method not specified or invalid", -32600)

    if "params" in request and not isinstance(request["params"], (dict, list)):
        raise RpcError("Invalid params container", -32600)

    if "id" in request:
        request_id = request["id"]
        if (
            isinstance(request_id, bool)
            or not isinstance(request_id, (str, int, float, type(None)))
            or (isinstance(request_id, float) and not math.isfinite(request_id))
        ):
            raise RpcError("Invalid request id", -32600)

