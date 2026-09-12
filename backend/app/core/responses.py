from typing import Any


def success(data: Any = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": True, "data": data, "meta": meta or {}}
