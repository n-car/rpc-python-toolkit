# RPC Python Toolkit

Framework-agnostic JSON-RPC 2.0 toolkit for Python.

This package is the early Python implementation for the RPC Toolkit ecosystem. It focuses on a small core that can be used directly or adapted later to ASGI/WSGI frameworks such as FastAPI, Starlette, Flask, or Django.

## Project Status

Early development package.

- The PyPI package name `rpc-python-toolkit` is currently unclaimed based on `pip index versions rpc-python-toolkit` returning no matching distribution on 2026-06-11.
- This package is not published to PyPI yet.
- Standard JSON-RPC 2.0 remains the default behavior.
- Safe Mode follows the same `X-RPC-Safe-Enabled` and value marker conventions used by `rpc-express-toolkit`.

## Installation

Until the first PyPI publication, install from GitHub or from a local checkout:

```bash
pip install git+https://github.com/n-car/rpc-python-toolkit.git
```

For local development:

```bash
pip install -e .
python -m unittest discover
```

## Current Scope

- Framework-independent `RpcEndpoint`
- Standard JSON-RPC calls, notifications, and batch requests
- `RpcClient` and `RpcSafeClient` over HTTP using Python standard library
- JSON Schema validation through `jsonschema`
- Optional RPC Toolkit Safe Mode over HTTP headers
- Method introspection with `__rpc.*` methods

## Quick Start

```python
from rpc_python_toolkit import RpcEndpoint

rpc = RpcEndpoint(enable_introspection=True)

def test(request, context, params):
    return {"ok": True, "params": params}

rpc.add_method("test", test)

response = rpc.handle_payload({
    "jsonrpc": "2.0",
    "method": "test",
    "params": {"value": 123},
    "id": 1,
})

print(response.body)
```

Result:

```json
{"jsonrpc": "2.0", "id": 1, "result": {"ok": true, "params": {"value": 123}}}
```

## HTTP Client

```python
from rpc_python_toolkit import RpcClient

client = RpcClient("http://localhost:3000/api")
result = client.call("test", {"value": 123})
```

## Safe Mode

Use `RpcSafeEndpoint` and `RpcSafeClient` when both sides support RPC Toolkit Safe Mode:

```python
from rpc_python_toolkit import RpcSafeEndpoint, RpcSafeClient

rpc = RpcSafeEndpoint()
client = RpcSafeClient("http://localhost:3000/api")
```

Safe Mode enables `X-RPC-Safe-Enabled` negotiation and recursive value encoding/decoding:

- strings are encoded as `S:<value>`
- datetimes are encoded as `D:<iso-date>`
- large integers are encoded as `<digits>n`

Python exposes arbitrary precision integers as `int`. BigInt marker strings from other RPC Toolkit implementations are decoded to Python `int` values when they are real markers, while literal marker-like strings are protected by the `S:` prefix in Safe Mode.

## Related Projects

- [rpc-express-toolkit](https://github.com/n-car/rpc-express-toolkit)
- [rpc-node-toolkit](https://github.com/n-car/rpc-node-toolkit)
- [rpc-toolkit-js-client](https://github.com/n-car/rpc-toolkit-js-client)
- [rpc-dotnet-toolkit](https://github.com/n-car/rpc-dotnet-toolkit)
- [rpc-java-toolkit](https://github.com/n-car/rpc-java-toolkit)
- [rpc-php-toolkit](https://github.com/n-car/rpc-php-toolkit)
- [rpc-arduino-toolkit](https://github.com/n-car/rpc-arduino-toolkit)
- [node-red-contrib-rpc-toolkit](https://github.com/n-car/node-red-contrib-rpc-toolkit)

## License

MIT. See [LICENSE](LICENSE).
