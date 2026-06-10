from __future__ import annotations


class RpcError(Exception):
    """JSON-RPC error with code and optional data."""

    def __init__(self, message: str, code: int = -32603, data: object = None):
        super().__init__(message)
        self.code = code
        self.data = data


class RpcRemoteError(RpcError):
    """Error returned by a remote JSON-RPC endpoint."""


