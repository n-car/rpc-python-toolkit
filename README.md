# RPC Python Toolkit

[![CI](https://github.com/n-car/rpc-python-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/n-car/rpc-python-toolkit/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/rpc-python-toolkit.svg)](https://pypi.org/project/rpc-python-toolkit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/rpc-python-toolkit.svg)](https://pypi.org/project/rpc-python-toolkit/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://pypi.org/project/rpc-python-toolkit/)

Framework-agnostic JSON-RPC 2.0 toolkit for Python.

Use this package when you need a small Python JSON-RPC 2.0 client/server core that can be embedded directly or adapted to HTTP frameworks. It follows the same protocol conventions used across the RPC Toolkit ecosystem.

## Project Status

Alpha package with the core JSON-RPC behavior implemented.

- Published on PyPI as `rpc-python-toolkit`.
- Standard JSON-RPC 2.0 remains the default behavior.
- Safe Mode follows the same `X-RPC-Safe-Enabled` and value marker conventions used by `rpc-express-toolkit`.
- The public API may still change before a stable Python release.

## Release Notes

### 0.2.1 - 2026-10-12

- Sanitize unexpected errors and `RpcError(-32603)` by default, removing internal messages and data while preserving explicit application errors.
- Validate request envelopes and reject non-JSON numeric constants, scalar/null parameters, boolean IDs, and non-finite IDs.
- Return errors for invalid batch elements, distinguish explicit null IDs from notifications, and preserve JSON payload shapes.
- Add error-handling and protocol regression tests, and document the tightened wire contract and trusted handler context.

## Installation

Install from PyPI:

```bash
pip install rpc-python-toolkit
```

For development snapshots, install from GitHub or from a local checkout:

```bash
pip install git+https://github.com/n-car/rpc-python-toolkit.git
```

For local development:

```bash
pip install -e .
python -m unittest discover
```

## What Is Implemented

- Framework-independent `RpcEndpoint`
- Standard JSON-RPC calls, notifications, and batch requests
- `RpcClient` and `RpcSafeClient` over HTTP using Python standard library
- JSON Schema validation through `jsonschema`
- Optional RPC Toolkit Safe Mode over HTTP headers
- Method introspection with `__rpc.*` methods

## What Is Not Implemented Yet

- Built-in ASGI/WSGI adapters for FastAPI, Starlette, Flask, or Django
- Async endpoint handlers
- OpenRPC export
- Built-in HTTP server adapters

## Quick Start

```python
from rpc_python_toolkit import RpcEndpoint

rpc = RpcEndpoint(
    enable_introspection=True,
    enable_batch=True,
    max_batch_size=100,
)

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

Batch can be disabled with `enable_batch=False`. Introspection remains opt-in.
Unexpected errors and `RpcError` instances with code `-32603` return only
`Internal error` by default, without internal messages or data. Other explicit
`RpcError` codes, messages, and data are preserved. Parse errors omit diagnostic
data. Use `sanitize_errors=False` only for local debugging to restore details.

Only valid requests without an `id` are notifications. An explicit `id: null`
receives a response; malformed envelopes (including scalar/null `params` or
boolean/non-finite IDs) return `-32600` with `id: null`. Method parameter schema
errors remain `-32602`.
Malformed JSON, including the non-JSON constants `NaN`, `Infinity`, and `-Infinity`,
returns `-32700`. Invalid elements in a batch produce individual error responses;
valid notifications remain silent even when their method fails. Objects, arrays,
and null results retain their JSON shapes.

When both application and request contexts are dictionaries, handlers receive a
merged dictionary and request values take precedence. For a non-dictionary
application context plus request data, handlers receive `RpcCallContext` with
separate `application` and `request` attributes.
These contexts are supplied by application/adapter code. Client `params` remain a
separate third handler argument and cannot replace trusted context.

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

Safe Mode transforms payload values, not method names, request IDs, error codes,
or error messages. Application `RpcError.data` is encoded like a result; sanitized
internal errors expose neither their original message nor their data.

## Examples

Runnable examples are available in [`examples/`](examples/):

- [`basic_server.py`](examples/basic_server.py) - direct endpoint usage without an HTTP adapter.
- [`basic_client.py`](examples/basic_client.py) - standard HTTP client call against an in-process endpoint.
- [`schema_validation.py`](examples/schema_validation.py) - method schema validation and JSON-RPC error output.
- [`safe_mode.py`](examples/safe_mode.py) - `RpcSafeClient` to `RpcSafeEndpoint` round-trip for strings, dates, and large integers.

For local checkout usage:

```bash
PYTHONPATH=src python3 examples/basic_server.py
PYTHONPATH=src python3 examples/basic_client.py
PYTHONPATH=src python3 examples/schema_validation.py
PYTHONPATH=src python3 examples/safe_mode.py
```

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
