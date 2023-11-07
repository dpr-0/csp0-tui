from typing import Any, Optional


class Cache:
    data: dict[str, Any] = {}

    @classmethod
    def set(cls, name: str, value: Any):
        cls.data[name] = value

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        return cls.data.get(name)
