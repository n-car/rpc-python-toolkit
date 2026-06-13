from __future__ import annotations

import json

from rpc_python_toolkit import RpcEndpoint


rpc = RpcEndpoint()

rpc.add_method(
    "math.add",
    lambda _request, _context, params: params["a"] + params["b"],
    schema={
        "type": "object",
        "required": ["a", "b"],
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "additionalProperties": False,
    },
)

valid = rpc.handle_payload(
    {
        "jsonrpc": "2.0",
        "method": "math.add",
        "params": {"a": 2, "b": 3},
        "id": 1,
    }
)

invalid = rpc.handle_payload(
    {
        "jsonrpc": "2.0",
        "method": "math.add",
        "params": {"a": 2},
        "id": 2,
    }
)

print(
    json.dumps(
        {
            "valid": valid.body,
            "invalid": invalid.body,
        },
        indent=2,
    )
)
