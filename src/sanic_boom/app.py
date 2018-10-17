import re
import warnings
from asyncio import CancelledError
from inspect import isawaitable
from traceback import format_exc
from urllib.parse import urlencode, urlunparse

from sanic import Sanic
from sanic.constants import HTTP_METHODS
from sanic.exceptions import SanicException, URLBuildError
from sanic.log import error_logger
from sanic.response import HTTPResponse, StreamingHTTPResponse

from sanic_boom.cache import CacheEngine
from sanic_boom.component import Component
from sanic_boom.references import DOC_LINKS as dl
from sanic_boom.request import BoomRequest
from sanic_boom.resolver import Resolver
from sanic_boom.router import BoomRouter
from sanic_boom.utils import param_parser
from sanic_boom.wrappers import MiddlewareType


class SanicBoom(Sanic):
    def __init__(self, *args, **kwargs):
        if "router" in kwargs:
            kwargs.pop("router")
        if "request_class" in kwargs:
            kwargs.pop("request_class")
        kwargs["router"] = BoomRouter()
        kwargs["request_class"] = BoomRequest
        components = kwargs.pop("components", [])
        resolver_cls = kwargs.pop("resolver_cls", Resolver)
        cache_engine_cls = kwargs.pop("cache_engine_cls", CacheEngine)
        param_parser_callable = kwargs.pop("param_parser", param_parser)
        super().__init__(*args, **kwargs)
        self.param_parser = param_parser_callable
        self.resolver = resolver_cls(self)
        self.cache_engine = cache_engine_cls(self)

        for component in components:
            self.add_component(component)

    def add_component(self, component: Component):
        self.resolver.add_component(component)

    def url_for(
        self,
        view_name: str,
        _anchor: str = "",
        _external: bool = False,
        _scheme: str = "",
        _server: str = None,
        _method: object = None,
        **kwargs
    ):
        # ? i think this should be in the Router
        uri, route = self.router.find_route_by_view_name(view_name)

        if not (uri and route):
            raise URLBuildError(
                "Endpoint with name `{}` was not found".format(view_name)
            )

        if _scheme and not _external:
            raise ValueError("When specifying _scheme, _external must be True")

        if _server is None and _external:
            _server = self.config.get("SERVER_NAME", "")

        if _external:
            if not _scheme:
                if ":" in _server[:8]:
                    _scheme = _server[:8].split(":", 1)[0]
                else:
                    _scheme = "http"

            if "://" in _server[:8]:
                _server = _server.split("://", 1)[-1]

        orig_uri = uri
        replaced_vars = []

        for k in kwargs:
            if re.search(r"([:|\*])", str(kwargs[k])):
                raise URLBuildError(
                    "The parameter '{}' passed for URL `{}` with the value of "
                    "'{}' may contain invalid characters that can break the "
                    "URL".format(k, orig_uri, kwargs[k])
                )

            m = re.search(r"([:|\*]{})".format(k), uri)
            if m:
                replaced_vars.append(k)
                uri = uri.replace(m.group(0), str(kwargs[k]))
            # else log ?

        for k in replaced_vars:
            del kwargs[k]

        if uri.find(":") > -1 or uri.find("*") > -1:
            raise URLBuildError(
                "Required parameters for URL `{}` was not passed to "
                "url_for".format(orig_uri)
            )

        # parse the remainder of the keyword arguments into a querystring
        query_string = urlencode(kwargs, doseq=True) if kwargs else ""
        # scheme://netloc/path;parameters?query#fragment
        return urlunparse((_scheme, _server, uri, "", query_string, _anchor))

    def route(
        self,
        uri,
        methods=None,
        host=None,
        strict_slashes=None,
        stream=False,
        version=None,
        name=None,
    ):
        """Decorate a function to be registered as a route
        :param uri: path of the URL
        :param methods: list or tuple of methods allowed
        :param host:
        :param strict_slashes:
        :param stream:
        :param version:
        :param name: user defined route name for url_for
        :return: decorated function
        """
        if not uri.startswith("/"):
            uri = "/" + uri

        if methods is None:
            methods = ["GET"]
        elif isinstance(methods, (frozenset, set)):
            methods = list(methods)

        if stream:  # noqa | do I really need to bother with this? For now?
            self.is_request_stream = True

        def response(handler):
            if stream:  # noqa I have no idea how to handle this right now
                handler.is_stream = stream
            self.router.add(uri, methods, handler, version=version, name=name)
            return handler

        return response

    def middleware(self, *args, **kwargs):
        """Create a middleware from a decorated function."""

        def register_middleware(_middleware):
            self.register_middleware(middleware=_middleware, **kwargs)
            return _middleware

        # Detect which way this was called, @middleware or @middleware('AT')
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            middleware = args[0]
            args = []
            return register_middleware(middleware)
        else:
            return register_middleware

    def register_middleware(self, middleware, attach_to="request", **kwargs):
        if "uri" not in kwargs and "methods" not in kwargs:
            if attach_to == "request":
                self.request_middleware.append(middleware)
            if attach_to == "response":
                self.response_middleware.appendleft(middleware)
            return middleware

        uri = kwargs.pop("uri", "/")
        methods = list(kwargs.pop("methods", HTTP_METHODS))

        if not uri.startswith("/"):
            uri = "/" + uri

        kwargs.update(
            {
                "uri": uri,
                "methods": methods,
                "is_middleware": True,
                "attach_to": MiddlewareType[attach_to.upper()],
                "handler": middleware,
            }
        )

        self.router.add(**kwargs)
        return middleware

    async def handle_request(self, request, write_callback, stream_callback):
        # Define `response` var here to remove warnings about
        # allocation before assignment below.
        response = None
        cancelled = False
        middlewares = []
        try:
            # --------------------------------------------------------------- #
            # request "global" middlewares
            # --------------------------------------------------------------- #
            request.app = self
            if self.request_middleware:
                response = await self._run_request_middleware(
                    request, self.request_middleware
                )
            # No middleware result
            if not response:
                # Fetch handler from router
                handler, middlewares, kwargs, uri = self.router.get(request)
                request.uri_template = uri
                # handler = self.request.route_handlers.endpoint
                # middlewares = self.request.route_handlers.middlewares
                # kwargs = self.request.route_params

                # run layered request middlewares
                request_middleware = [
                    m.handler
                    for m in middlewares
                    if m.attach_to == MiddlewareType.REQUEST
                ]

                if request_middleware:
                    response = await self._run_request_middleware(
                        request, request_middleware
                    )

                if not response:
                    # run response handler
                    ret = await self.resolver.resolve(
                        request=request, func=handler, prefetched=kwargs
                    )
                    response = handler(**ret)
                    if isawaitable(response):
                        response = await response
        except CancelledError:
            # If response handler times out, the server handles the error
            # and cancels the handle_request job.
            # In this case, the transport is already closed and we cannot
            # issue a response.
            response = None
            cancelled = True
        except Exception as e:  # noqa this was copied from Sanic "as is"
            # -------------------------------------------- #
            # Response Generation Failed
            # -------------------------------------------- #

            try:
                response = self.error_handler.response(request, e)
                if isawaitable(response):
                    response = await response
            except Exception as e:
                if isinstance(e, SanicException):
                    response = self.error_handler.default(
                        request=request, exception=e
                    )
                elif self.debug:
                    response = HTTPResponse(
                        "Error while handling error: {}\nStack: {}".format(
                            e, format_exc()
                        ),
                        status=500,
                    )
                else:
                    response = HTTPResponse(
                        "An error occurred while handling an error", status=500
                    )
        finally:
            # --------------------------------------------------------------- #
            # Response Middleware
            # --------------------------------------------------------------- #
            # Don't run response middleware if response is None
            if response is not None:
                try:
                    if self.response_middleware:
                        response = await self._run_response_middleware(
                            request, response, self.response_middleware
                        )
                    # run layered response middlewares
                    response_middleware = [
                        m.handler
                        for m in middlewares
                        if m.attach_to == MiddlewareType.RESPONSE
                    ]

                    if response_middleware:
                        response = await self._run_response_middleware(
                            request, response, response_middleware
                        )

                except CancelledError:
                    # Response middleware can timeout too, as above.
                    response = None
                    cancelled = True
                except BaseException:
                    error_logger.exception(
                        "Exception occurred in one of response "
                        "middleware handlers"
                    )
            if cancelled:
                raise CancelledError()

        # pass the response to the correct callback
        if isinstance(response, StreamingHTTPResponse):  # noqa copied code
            await stream_callback(response)
        else:
            write_callback(response)

    async def _run_request_middleware(self, request, middlewares):
        for middleware in middlewares:
            ret = await self.resolver.resolve(request=request, func=middleware)
            response = middleware(**ret)
            if isawaitable(response):
                response = await response
            if response:
                return response
        return None

    async def _run_response_middleware(self, request, response, middlewares):
        for middleware in middlewares:
            ret = await self.resolver.resolve(
                request=request,
                func=middleware,
                prefetched={"response": response},
            )
            _response = middleware(**ret)
            if isawaitable(_response):
                _response = await _response
            if _response:
                response = _response
                break
        return response

    # ----------------------------------------------------------------------- #
    # what doesn't make any sense for building APIs
    # ----------------------------------------------------------------------- #

    def static(
        self,
        uri,
        file_or_directory,
        pattern=r"/?.+",
        use_modified_since=True,
        use_content_range=False,
        stream_large_files=False,
        name="static",
        host=None,
        strict_slashes=None,
        content_type=None,
    ):
        warnings.warn(
            "'sanic-boom' is not meant to be used with static file handling. "
            "For more information, see: {}".format(dl.get("SanicBoom.static")),
            RuntimeWarning,
        )

    def remove_route(self, uri, clean_cache=True, host=None):
        warnings.warn(
            "Removing routes is not available on 'sanic-boom' for design "
            "reasons. Read more here: {}".format(
                dl.get("SanicBoom.remove_route")
            ),
            RuntimeWarning,
        )
