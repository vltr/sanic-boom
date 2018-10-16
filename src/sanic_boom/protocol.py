from sanic.exceptions import PayloadTooLarge
from sanic.server import HttpProtocol


class BoomProtocol(HttpProtocol):
    """This protocol is just needed because of this PR for the time being:
    https://github.com/huge-success/sanic/pull/1310
    """

    def on_url(self, url):  # noqa # ? is fragmentation still an issue?
        self.url = url

    def on_header(
        self, name, value
    ):  # noqa # ? is fragmentation still an issue?
        if name == b"Content-Length" and int(value) > self.request_max_size:
            self.write_error(PayloadTooLarge("Payload too large"))
        try:
            value = value.decode()
        except UnicodeDecodeError:
            value = value.decode("latin_1")
        self.headers.append((name.decode().casefold(), value))

    def on_body(self, body):
        if self.is_request_stream and self._is_stream_handler:  # noqa
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
        if self.is_request_stream and self._is_stream_handler:  # noqa
            self._request_stream_task = self.loop.create_task(
                self.request.stream.put(None)
            )
            return

        # # ! get everything we need to see if this request should proceed or not
        # try:
        #     handler, middlewares, params, uri = self.router.get(self.request)
        #     self.request.uri_template = uri
        #     self.request.route_params = params
        #     self.request.route_handlers = Handler(
        #         endpoint=handler, middlewares=middlewares
        #     )
        # except (MethodNotSupported, NotFound) as e:
        #     self.write_error(e)

        self.request.body_finish()
        self.execute_request_handler()
