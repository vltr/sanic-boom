import asyncio
import traceback
from functools import partial
from time import time

from httptools import HttpRequestParser
from httptools.parser.errors import HttpParserError
from multidict import CIMultiDict
from sanic.exceptions import InvalidUsage
from sanic.exceptions import PayloadTooLarge
from sanic.exceptions import RequestTimeout
from sanic.exceptions import ServerError
from sanic.exceptions import ServiceUnavailable
from sanic.log import access_logger
from sanic.log import logger
from sanic.request import Request
from sanic.response import HTTPResponse
from sanic.server import Signal

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


_CURRENT_TIME = time()


class BoomProtocol(asyncio.Protocol):
    __slots__ = (
        # event loop, connection
        "loop",
        "transport",
        "connections",
        "signal",
        # request params
        "parser",
        "request",
        "url",
        "headers",
        # request config
        "request_handler",
        "request_timeout",
        "response_timeout",
        "keep_alive_timeout",
        "request_max_size",
        "request_class",
        "is_request_stream",
        "router",
        # enable or disable access log purpose
        "access_log",
        # connection management
        "_total_request_size",
        "_request_timeout_handler",
        "_response_timeout_handler",
        "_keep_alive_timeout_handler",
        "_last_request_time",
        "_last_response_time",
        "_is_stream_handler",
        "_not_paused",
    )

    def __init__(
        self,
        *,
        loop,
        request_handler,
        error_handler,
        signal=Signal(),
        connections=set(),
        request_timeout=60,
        response_timeout=60,
        keep_alive_timeout=5,
        request_max_size=None,
        request_class=None,
        access_log=True,
        keep_alive=True,
        is_request_stream=False,
        router=None,
        state=None,
        debug=False,
        **kwargs
    ):
        self.loop = loop
        self.transport = None
        self.request = None
        self.parser = None
        self.url = None
        self.headers = None
        self.router = router
        self.signal = signal
        self.access_log = access_log
        self.connections = connections
        self.request_handler = request_handler
        self.error_handler = error_handler
        self.request_timeout = request_timeout
        self.response_timeout = response_timeout
        self.keep_alive_timeout = keep_alive_timeout
        self.request_max_size = request_max_size
        self.request_class = request_class or Request
        self.is_request_stream = is_request_stream
        self._is_stream_handler = False
        self._not_paused = asyncio.Event(loop=loop)
        self._total_request_size = 0
        self._request_timeout_handler = None
        self._response_timeout_handler = None
        self._keep_alive_timeout_handler = None
        self._last_request_time = None
        self._last_response_time = None
        self._request_handler_task = None
        self._request_stream_task = None
        self._keep_alive = keep_alive
        self.state = state if state else {}
        if "requests_count" not in self.state:
            self.state["requests_count"] = 0
        self._debug = debug
        self._not_paused.set()

    @property
    def keep_alive(self):
        return (
            self._keep_alive
            and not self.signal.stopped
            and self.parser.should_keep_alive()
        )

    # ----------------------------------------------------------------------- #
    # Connection
    # ----------------------------------------------------------------------- #

    def connection_made(self, transport):
        self.connections.add(self)
        self._request_timeout_handler = self.loop.call_later(
            self.request_timeout, self.request_timeout_callback
        )
        self.transport = transport
        self._last_request_time = _CURRENT_TIME

    def connection_lost(self, exc):
        self.connections.discard(self)
        if self._request_timeout_handler:
            self._request_timeout_handler.cancel()
        if self._response_timeout_handler:
            self._response_timeout_handler.cancel()
        if self._keep_alive_timeout_handler:
            self._keep_alive_timeout_handler.cancel()

    def pause_writing(self):
        self._not_paused.clear()

    def resume_writing(self):
        self._not_paused.set()

    def request_timeout_callback(self):
        # See the docstring in the RequestTimeout exception, to see
        # exactly what this timeout is checking for.
        # Check if elapsed time since request initiated exceeds our
        # configured maximum request timeout value
        time_elapsed = _CURRENT_TIME - self._last_request_time
        if time_elapsed < self.request_timeout:
            time_left = self.request_timeout - time_elapsed
            self._request_timeout_handler = self.loop.call_later(
                time_left, self.request_timeout_callback
            )
        else:
            if self._request_stream_task:
                self._request_stream_task.cancel()
            if self._request_handler_task:
                self._request_handler_task.cancel()
            exception = RequestTimeout("Request timeout")
            self.write_error(exception)

    def response_timeout_callback(self):
        # Check if elapsed time since response was initiated exceeds our
        # configured maximum request timeout value
        time_elapsed = _CURRENT_TIME - self._last_request_time
        if time_elapsed < self.response_timeout:
            time_left = self.response_timeout - time_elapsed
            self._response_timeout_handler = self.loop.call_later(
                time_left, self.response_timeout_callback
            )
        else:
            if self._request_stream_task:
                self._request_stream_task.cancel()
            if self._request_handler_task:
                self._request_handler_task.cancel()
            exception = ServiceUnavailable("Response timeout")
            self.write_error(exception)

    def keep_alive_timeout_callback(self):
        # Check if elapsed time since last response exceeds our configured
        # maximum keep alive timeout value
        time_elapsed = _CURRENT_TIME - self._last_response_time
        if time_elapsed < self.keep_alive_timeout:
            time_left = self.keep_alive_timeout - time_elapsed
            self._keep_alive_timeout_handler = self.loop.call_later(
                time_left, self.keep_alive_timeout_callback
            )
        else:
            logger.debug("Keep alive timeout. Closing connection")
            self.transport.close()
            self.transport = None

    # ----------------------------------------------------------------------- #
    # Parsing
    # ----------------------------------------------------------------------- #

    def data_received(self, data):
        # Check for the request itself getting too large and exceeding
        # memory limits
        self._total_request_size += len(data)
        if self._total_request_size > self.request_max_size:
            exception = PayloadTooLarge("Payload too large")
            self.write_error(exception)

        # Create parser if this is the first time we're receiving data
        if self.parser is None:
            assert self.request is None
            self.headers = []
            self.parser = HttpRequestParser(self)

        # requests count
        self.state["requests_count"] = self.state["requests_count"] + 1

        # Parse request chunk or close connection
        try:
            self.parser.feed_data(data)
        except HttpParserError:
            message = "Bad Request"
            if self._debug:
                message += "\n" + traceback.format_exc()
            exception = InvalidUsage(message)
            self.write_error(exception)

    def on_url(self, url):
        self.url = url

    def on_header(self, name, value):
        if name == b"Content-Length" and int(value) > self.request_max_size:
            exception = PayloadTooLarge("Payload too large")
            self.write_error(exception)
        try:
            value = value.decode()
        except UnicodeDecodeError:
            value = value.decode("latin_1")
        self.headers.append((name.decode().casefold(), value))

    def on_headers_complete(self):
        # create the request object
        self.request = self.request_class(
            url_bytes=self.url,
            headers=CIMultiDict(self.headers),
            version=self.parser.get_http_version(),
            method=self.parser.get_method().decode(),
            transport=self.transport,
        )
        """
        # get everything we need to see if this request should proceed or not
        handler, middlewares, params, uri = self.router.get(self.request)
        if handler is None:
            # there is no handler, why should we continue?
            exception = ServerError("'None' was returned while requesting a "
                                    "handler from the router")
            self.write_error(exception)
            return  # TODO is this needed?
        self.request["_from_router"] = {
            "handler": handler,
            "middlewares": middlewares,
            "params": params,
            "uri": uri
        }
        """
        # Remove any existing KeepAlive handler here,
        # It will be recreated if required on the new request.
        if self._keep_alive_timeout_handler:
            self._keep_alive_timeout_handler.cancel()
            self._keep_alive_timeout_handler = None
        if self.is_request_stream:
            self._is_stream_handler = self.router.is_stream_handler(
                self.request
            )
            if self._is_stream_handler:
                self.request.stream = asyncio.Queue()
                self.execute_request_handler()

    def on_body(self, body):
        if self.is_request_stream and self._is_stream_handler:
            self._request_stream_task = self.loop.create_task(
                self.request.stream.put(body)
            )
            return
        self.request.body_append(body)

    def on_message_complete(self):
        # Entire request (headers and whole body) is received.
        # We can cancel and remove the request timeout handler now.
        if self._request_timeout_handler:
            self._request_timeout_handler.cancel()
            self._request_timeout_handler = None
        if self.is_request_stream and self._is_stream_handler:
            self._request_stream_task = self.loop.create_task(
                self.request.stream.put(None)
            )
            return
        self.request.body_finish()
        self.execute_request_handler()

    def execute_request_handler(self):
        self._response_timeout_handler = self.loop.call_later(
            self.response_timeout, self.response_timeout_callback
        )
        self._last_request_time = _CURRENT_TIME
        self._request_handler_task = self.loop.create_task(
            self.request_handler(
                self.request, self.write_response, self.stream_response
            )
        )

    # ----------------------------------------------------------------------- #
    # Responding
    # ----------------------------------------------------------------------- #
    def log_response(self, response):
        if self.access_log:
            extra = {"status": getattr(response, "status", 0)}

            if isinstance(response, HTTPResponse):
                extra["byte"] = len(response.body)
            else:
                extra["byte"] = -1

            extra["host"] = "UNKNOWN"
            if self.request is not None:
                if self.request.ip:
                    extra["host"] = "{0}:{1}".format(
                        self.request.ip, self.request.port
                    )

                extra["request"] = "{0} {1}".format(
                    self.request.method, self.request.url
                )
            else:
                extra["request"] = "nil"

            access_logger.info("", extra=extra)

    def write_response(self, response):
        """
        Writes response content synchronously to the transport.
        """
        if self._response_timeout_handler:
            self._response_timeout_handler.cancel()
            self._response_timeout_handler = None
        try:
            keep_alive = self.keep_alive
            self.transport.write(
                response.output(
                    self.request.version, keep_alive, self.keep_alive_timeout
                )
            )
            self.log_response(response)
        except AttributeError:
            logger.error(
                "Invalid response object for url %s, "
                "Expected Type: HTTPResponse, Actual Type: %s",
                self.url,
                type(response),
            )
            self.write_error(ServerError("Invalid response type"))
        except RuntimeError:
            if self._debug:
                logger.error(
                    "Connection lost before response written @ %s",
                    self.request.ip,
                )
            keep_alive = False
        except Exception as e:
            self.bail_out(
                "Writing response failed, connection closed {}".format(repr(e))
            )
        finally:
            if not keep_alive:
                self.transport.close()
                self.transport = None
            else:
                self._keep_alive_timeout_handler = self.loop.call_later(
                    self.keep_alive_timeout, self.keep_alive_timeout_callback
                )
                self._last_response_time = _CURRENT_TIME
                self.cleanup()

    async def drain(self):
        await self._not_paused.wait()

    def push_data(self, data):
        self.transport.write(data)

    async def stream_response(self, response):
        """
        Streams a response to the client asynchronously. Attaches
        the transport to the response so the response consumer can
        write to the response as needed.
        """
        if self._response_timeout_handler:
            self._response_timeout_handler.cancel()
            self._response_timeout_handler = None

        try:
            keep_alive = self.keep_alive
            response.protocol = self
            await response.stream(
                self.request.version, keep_alive, self.keep_alive_timeout
            )
            self.log_response(response)
        except AttributeError:
            logger.error(
                "Invalid response object for url %s, "
                "Expected Type: HTTPResponse, Actual Type: %s",
                self.url,
                type(response),
            )
            self.write_error(ServerError("Invalid response type"))
        except RuntimeError:
            if self._debug:
                logger.error(
                    "Connection lost before response written @ %s",
                    self.request.ip,
                )
            keep_alive = False
        except Exception as e:
            self.bail_out(
                "Writing response failed, connection closed {}".format(repr(e))
            )
        finally:
            if not keep_alive:
                self.transport.close()
                self.transport = None
            else:
                self._keep_alive_timeout_handler = self.loop.call_later(
                    self.keep_alive_timeout, self.keep_alive_timeout_callback
                )
                self._last_response_time = _CURRENT_TIME
                self.cleanup()

    def write_error(self, exception):
        # An error _is_ a response.
        # Don't throw a response timeout, when a response _is_ given.
        if self._response_timeout_handler:
            self._response_timeout_handler.cancel()
            self._response_timeout_handler = None
        response = None
        try:
            response = self.error_handler.response(self.request, exception)
            version = self.request.version if self.request else "1.1"
            self.transport.write(response.output(version))
        except RuntimeError:
            if self._debug:
                logger.error(
                    "Connection lost before error written @ %s",
                    self.request.ip if self.request else "Unknown",
                )
        except Exception as e:
            self.bail_out(
                "Writing error failed, connection closed {}".format(repr(e)),
                from_error=True,
            )
        finally:
            if self.parser and (
                self.keep_alive or getattr(response, "status", 0) == 408
            ):
                self.log_response(response)
            try:
                self.transport.close()
            except AttributeError as e:
                logger.debug("Connection lost before server could close it.")

    def bail_out(self, message, from_error=False):
        if from_error or self.transport.is_closing():
            logger.error(
                "Transport closed @ %s and exception "
                "experienced during error handling",
                self.transport.get_extra_info("peername"),
            )
            logger.debug("Exception:\n%s", traceback.format_exc())
        else:
            exception = ServerError(message)
            self.write_error(exception)
            logger.error(message)

    def cleanup(self):
        """This is called when KeepAlive feature is used,
        it resets the connection in order for it to be able
        to handle receiving another request on the same connection."""
        self.parser = None
        self.request = None
        self.url = None
        self.headers = None
        self._request_handler_task = None
        self._request_stream_task = None
        self._total_request_size = 0
        self._is_stream_handler = False

    def close_if_idle(self):
        """Close the connection if a request is not being sent or received

        :return: boolean - True if closed, false if staying open
        """
        if not self.parser:
            self.transport.close()
            return True
        return False

    def close(self):
        """
        Force close the connection.
        """
        if self.transport is not None:
            self.transport.close()
            self.transport = None


def update_current_time(loop):
    """Cache the current time, since it is needed at the end of every
    keep-alive request to update the request timeout time

    :param loop:
    :return:
    """
    global _CURRENT_TIME
    _CURRENT_TIME = time()
    loop.call_later(1, partial(update_current_time, loop))