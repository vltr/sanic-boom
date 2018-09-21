import warnings
from typing import NamedTuple

from sanic.exceptions import NotFound
from sanic.router import RouteExists
from xrtr import RadixTree

from sanic_boom.references import DOC_LINKS as dl

_Route = NamedTuple(
    "_Route",
    [("name", str), ("handler", object), ("methods", set), ("uri", str)],
)

_Middleware = NamedTuple(
    "_Middleware",
    [("handler", object), ("methods", set), ("uri", str), ("attach_to", str)],
)


class Router:
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
        **kwargs
    ):
        is_middleware = kwargs.pop("is_middleware", False)
        # uri "normalization", there is no strict slashes for mental sakeness
        uri = uri.strip()
        if uri.count("/") > 1:
            uri = uri.rstrip("/")  # yes, yes yes and yes! (:
        try:
            if methods:
                methods = frozenset(methods)
            if is_middleware:
                attach_to = kwargs.pop("attach_to", "request")
                middleware = _Middleware(
                    handler=handler,
                    methods=methods,
                    uri=uri,
                    attach_to=attach_to,
                )
                self._tree.insert(uri, middleware, methods, True)
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

                route = _Route(
                    handler=handler,
                    methods=methods,
                    uri=uri,
                    name=handler_name,
                )
                self._tree.insert(uri, route, methods)

                if self.routes_names.get(handler_name) is None:
                    self.routes_names[handler_name] = (uri, route)
        except ValueError as ve:
            raise RouteExists from ve

    def find_route_by_view_name(self, view_name):
        # ------------------------------------------------------------------- #
        # code taken and adapted from the Sanic router
        # ------------------------------------------------------------------- #
        if not view_name:
            return (None, None)

        return self.routes_names.get(view_name, (None, None))

    def get(self, request):
        return self._get(request.path, request.method)

    def _get(self, url, method):
        # url "normalization", there is no strict slashes for mental sakeness
        url = url.strip()
        if url.count("/") > 1:
            url = url.rstrip("/")  # yes, yes yes and yes! (:
        route, middlewares, params = self._tree.get(url, method)
        if route is None:
            raise NotFound("Requested URL {} not found".format(url))
        # ------------------------------------------------------------------- #
        # code taken and adapted from the Sanic router
        # ------------------------------------------------------------------- #
        route_handler = route.handler
        if hasattr(route_handler, "handlers"):
            # W-W-WHY ?!
            route_handler = route_handler.handlers[method]
        return route_handler, middlewares, params, route.uri

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


__all__ = ("Router",)
