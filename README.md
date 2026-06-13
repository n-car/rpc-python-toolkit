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
