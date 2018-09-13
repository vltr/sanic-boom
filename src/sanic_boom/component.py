import inspect
from enum import IntEnum


class ComponentCache(IntEnum):
    NO_CACHE = 1
    REQUEST = 2
    ENDPOINT = 4
    CURRENT_THREAD = 8
    APP = 16


class Component:
    def __init__(self, app):
        self.app = app

    def get_cache_lifecycle(self) -> ComponentCache:
        return ComponentCache.NO_CACHE

    def resolve(self, param: inspect.Parameter) -> bool:
        raise NotImplementedError  # noqa

    async def get(self, *args, **kwargs):
        raise NotImplementedError  # noqa


__all__ = ("Component", "ComponentCache")
