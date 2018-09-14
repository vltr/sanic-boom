import warnings

from xrtr import RadixTree

from sanic_boom.references import DOC_LINKS as dl


class Router:
    def __init__(self):
        self._tree = RadixTree()

    @classmethod
    def parse_parameter_string(cls, parameter_string):
        warnings.warn(
            "This method is not available in 'sanic-boom'. You can check for "
            "more information between differences of the 'sanic-boom' router "
            "and Sanic default router: {}".format(
                dl.get("Router.parse_parameter_string")
            ),
            RuntimeWarning,
        )
        return None, None, None

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
        self._tree.insert(uri, handler, methods, is_middleware)

    def remove(self, *args, **kwargs):
        warnings.warn(
            "Removing routes is not available on 'sanic-boom' for design "
            "reasons. Read more here: {}".format(dl.get("Router.remove")),
            RuntimeWarning,
        )

    def find_route_by_view_name(self, view_name, name=None):
        pass

    def get(self, request):
        return self._tree.get(request.path, request.method)

    def get_supported_methods(self, url):
        pass

    def is_stream_handler(self, request):
        handler = request.get("_endpoint_handler")  # XXX WRONG! See bellow.
        if handler is None:
            # NOTE: this will always return False since it is called by
            # Server.on_headers_complete (which is prior to calling
            # Sanic.handle_request, that will again call Router.get,
            # as the original implementation of Sanic does). Something needs
            # to change so the Router.get won't get called twice.
            return False
        # the rest of the code is took from Sanic's Router.is_stream_handler
        if hasattr(handler, "view_class") and hasattr(
            handler.view_class, request.method.lower()
        ):
            handler = getattr(handler.view_class, request.method.lower())
        return hasattr(handler, "is_stream")


__all__ = ("Router",)
