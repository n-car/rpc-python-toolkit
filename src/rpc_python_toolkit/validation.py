from __future__ import annotations

from typing import Any

import jsonschema

from .errors import RpcError


class SchemaValidator:
    def validate(self, params: Any, schema: dict[str, Any] | None) -> None:
        if not schema:
            return

        try:
            jsonschema.validate(instance=params, schema=schema)
        except jsonschema.ValidationError as exc:
            raise RpcError(
                "Validation failed",
                -32602,
                {
                    "message": exc.message,
                    "path": list(exc.path),
                },
            ) from exc

