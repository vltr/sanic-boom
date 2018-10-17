import inspect
import typing as t
import warnings
from threading import local as t_local

from sanic_boom.component import Component, ComponentCache
from sanic_boom.references import DOC_LINKS as dl

_REQUEST_CACHE_KEY = "_sanic_boom_cache"


class CacheEngine:

    _thread_local = t_local()

    def __init__(self, app):
        self.app = app
        self._endpoints = {}

    async def get(
        self,
        component: Component,
        endpoint: t.Callable,
        request,
        param: inspect.Parameter,
    ):
        lifecycle = component.get_cache_lifecycle()
        value = None

        if lifecycle == ComponentCache.REQUEST:
            value = await self._resolve_request(component, request, param)
        elif lifecycle == ComponentCache.ENDPOINT:
            value = await self._resolve_endpoint(
                component, endpoint, request, param
            )
        elif lifecycle == ComponentCache.CURRENT_THREAD:
            value = await self._resolve_thread(component, request, param)
        elif lifecycle == ComponentCache.APP:
            value = await self._resolve_app(component, request, param)
        if value is not None:
            return value
        return await self._resolve_param(component, request, param)

    async def _resolve_param(
        self, component: Component, request, param: inspect.Parameter
    ) -> t.Dict[str, t.Any]:
        kw = await self.app.resolver.resolve(
            request=request, func=component.get, source_param=param
        )
        return await component.get(**kw)

    async def _resolve_request(
        self, component: Component, request, param: inspect.Parameter
    ) -> t.Dict[str, t.Any]:
        if (
            _REQUEST_CACHE_KEY in request
            and param in request[_REQUEST_CACHE_KEY]
        ):
            return request[_REQUEST_CACHE_KEY][param]
        return await self._evaluate_request(component, request, param)

    async def _evaluate_request(
        self, component: Component, request, param: inspect.Parameter
    ) -> t.Dict[str, t.Any]:
        value = await self._resolve_param(component, request, param)
        if _REQUEST_CACHE_KEY not in request:
            request[_REQUEST_CACHE_KEY] = {}
        request[_REQUEST_CACHE_KEY][param] = value
        return value

    async def _resolve_endpoint(
        self,
        component: Component,
        endpoint: t.Callable,
        request,
        param: inspect.Parameter,
    ) -> t.Dict[str, t.Any]:
        if endpoint in self._endpoints and param in self._endpoints[endpoint]:
            return self._endpoints[endpoint][param]
        return await self._evaluate_endpoint(
            component, endpoint, request, param
        )

    async def _evaluate_endpoint(
        self,
        component: Component,
        endpoint: t.Callable,
        request,
        param: inspect.Parameter,
    ) -> t.Dict[str, t.Any]:
        value = await self._resolve_param(component, request, param)
        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = {}
        self._endpoints[endpoint][param] = value
        return value

    async def _resolve_thread(
        self, component: Component, request, param: inspect.Parameter
    ) -> t.Dict[str, t.Any]:
        if (
            hasattr(self._thread_local, "sanic_boom_cache")
            and param in self._thread_local.sanic_boom_cache
        ):
            return self._thread_local.sanic_boom_cache[param]
        return await self._evaluate_thread(component, request, param)

    async def _evaluate_thread(
        self, component: Component, request, param: inspect.Parameter
    ) -> t.Dict[str, t.Any]:
        value = await self._resolve_param(component, request, param)
        if not hasattr(self._thread_local, "sanic_boom_cache"):
            self._thread_local.sanic_boom_cache = {}
        self._thread_local.sanic_boom_cache[param] = value
        return value

    async def _resolve_app(
        self, component: Component, request, param: inspect.Parameter
    ) -> t.Dict[str, t.Any]:
        warnings.warn(
            "This method relies on a custom implementation by the user. More "
            "information about how to implement, why and examples on "
            "{}".format(dl.get("CacheEngine._resolve_app")),
            RuntimeWarning,
        )
        return None


__all__ = ("CacheEngine",)
