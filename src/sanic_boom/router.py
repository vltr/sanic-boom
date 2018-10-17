import re
import warnings
from collections.abc import Iterable
from functools import lru_cache

from sanic.exceptions import MethodNotSupported, NotFound
from sanic.router import ROUTER_CACHE_SIZE, RouteExists
from xrtr import RadixTree

from sanic_boom.references import DOC_LINKS as dl
from sanic_boom.wrappers import Middleware, MiddlewareType, Route


class BoomRouter:
    def __init__(self):
        self._tree = RadixTree()
        self.routes_names = {}

    def add(
        self,
        uri,
        methods,
        handler,
        host=None,
        strict_slashes=False,
        version=None,
        name=None,
        is_middleware=False,
        attach_to=MiddlewareType.REQUEST,
        **kwargs  # ! is this necessary yet?
    ):
        # uri "normalization", there is no strict slashes for mental sakeness
        uri = uri.strip()

        if uri.count("/") > 1 and uri[-1] == "/":
            uri = uri[:-1]  # yes, yes yes and yes! (:

        if version is not None:
            version = re.escape(str(version).strip("/").lstrip("v"))
            uri = "/".join(["/v{}".format(version), uri.lstrip("/")])
        uri = re.sub(r"\/{2,}", "/", uri)

        try:
            if not isinstance(methods, Iterable):
                raise ValueError(
                    "Expected Iterable for methods, got {!r}".format(methods)
                )

            if isinstance(methods, str):
                methods = [methods]
            elif not isinstance(methods, list):
                methods = list(methods)

            if is_middleware:
                middleware = Middleware(handler=handler, attach_to=attach_to)
                self._tree.insert(uri, middleware, methods, no_conflict=True)

            else:
                handler_name = None  # old habits die hard
                # ----------------------------------------------------------- #
                # code taken and adapted from the Sanic router
                # ----------------------------------------------------------- #
                if hasattr(handler, "__blueprintname__"):
                    handler_name = "{}.{}".format(
                        handler.__blueprintname__, name or handler.__name__
                    )
                else:
                    handler_name = name or getattr(handler, "__name__", None)

                if self.routes_names.get(handler_name) is not None:
                    msg = (
                        "The given route with handler_name='{}' is already "
                        "registered or clashes with "
                        "another".format(handler_name)
                    )
                    raise RouteExists(msg)

                route = Route(
                    handler=handler,
                    methods=methods,
                    uri=uri,
                    name=handler_name,
                )
                self._tree.insert(path=uri, handler=route, methods=methods)
                self.routes_names[handler_name] = (uri, route)

        except KeyError as ke:
            raise RouteExists from ke

    def find_route_by_view_name(self, view_name):
        # ------------------------------------------------------------------- #
        # code taken and adapted from the Sanic router
        # ------------------------------------------------------------------- #
        if not view_name:
            return (None, None)

        return self.routes_names.get(view_name, (None, None))

    def get(self, request):
        return self._get(request.path, request.method)

    @lru_cache(maxsize=ROUTER_CACHE_SIZE)
    def _get(self, url, method):
        # url "normalization", there is no strict slashes for mental sakeness
        url = url.strip()

        if url.count("/") > 1 and url[-1] == "/":
            url = url[:-1]  # yes, yes yes and yes! (:
        route, middlewares, params = self._tree.get(url, method)

        if route is self._tree.sentinel:
            raise MethodNotSupported(
                "Method {} not allowed for URL {}".format(method, url),
                method=method,
                allowed_methods=self.get_supported_methods(url),
            )
        elif route is None:
            raise NotFound("Requested URL {} not found".format(url))
        # ------------------------------------------------------------------- #
        # code taken and adapted from the Sanic router
        # ------------------------------------------------------------------- #
        route_handler = route.handler

        if hasattr(route_handler, "handlers"):  # noqa
            # W-W-WHY ?! I don't even know what this is or why is it here
            route_handler = route_handler.handlers[method]
        return route_handler, middlewares, params, route.uri

    def get_supported_methods(self, url):
        return self._tree.methods_for(url)

    def is_stream_handler(self, request):
        warnings.warn(
            "NOTE: this will always return False since it is called by "
            "Server.on_headers_complete (which is prior to calling "
            "Sanic.handle_request, that will again call Router.get, as the "
            "original implementation of Sanic does). Something needs to "
            "change so the Router.get method won't get called twice. Read "
            "more here: {}".format(dl.get("Router.is_stream_handler")),
            RuntimeWarning,
        )
        return False


__all__ = ("BoomRouter",)
