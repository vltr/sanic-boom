import asyncio
import inspect
import logging
from io import StringIO

import pytest
from sanic.exceptions import ServiceUnavailable
from sanic.response import text

from sanic_boom import BoomRequest, BoomRouter, Component, SanicBoom


class FakeComponent(Component):  # noqa this is a very simple example
    def resolve(self, param: inspect.Parameter) -> bool:
        return False

    async def get(self, request):
        return {}


def test_initialization():
    app = SanicBoom(
        "test_initialization",
        router=object,
        request_class=object,
        components=[FakeComponent],
    )
    assert app.request_class == BoomRequest
    assert isinstance(app.router, BoomRouter)
    assert isinstance(app.resolver.components[0], FakeComponent)

    # i had to force using them to, well, work nice together ... sorry :-/

    with pytest.warns(RuntimeWarning):
        app.static("foo", "bar")

    with pytest.warns(RuntimeWarning):
        app.remove_route("/foo")


def test_no_arg_handler(app):
    @app.get("/")
    async def handler():
        return text("OK")

    request, response = app.test_client.get("/")
    assert response.status == 200
    assert response.text == "OK"


def test_args_kwargs_handler(app):
    @app.get("/")
    async def handler(*args, **kwargs):
        assert args == tuple()
        assert kwargs == {}
        return text("OK")

    request, response = app.test_client.get("/")
    assert response.status == 200
    assert response.text == "OK"


def test_prepend_slash(app):
    @app.middleware(uri="foo")
    async def my_middleware(request):
        request["foo_is_/foo"] = 1

    @app.get("foo")
    async def handler(request):
        return text("OK")

    request, response = app.test_client.get("/foo")
    assert response.status == 200
    assert response.text == "OK"
    assert request["foo_is_/foo"] == 1


def test_response_timeout_handler(app):

    app.config["RESPONSE_TIMEOUT"] = 1

    @app.route("/foo")
    async def handler(request):  # noqa
        await asyncio.sleep(3)
        return text("OK")

    @app.exception(ServiceUnavailable)
    def handler_exception(request, exception):
        return text("timeout", 503)

    request, response = app.test_client.get("/foo")
    assert response.status == 503
    assert response.text == "timeout"


def test_response_timeout_middleware(app):

    app.config["RESPONSE_TIMEOUT"] = 1

    @app.route("/foo")
    async def handler(request):  # noqa
        return text("OK")

    @app.middleware(uri="/", attach_to="response")
    async def response_middleware(request, response):
        # i will spend a lot of time here
        await asyncio.sleep(3)

    @app.exception(ServiceUnavailable)
    def handler_exception(request, exception):
        return text("timeout", 503)

    request, response = app.test_client.get("/foo")
    assert response.status == 503
    assert response.text == "timeout"


def test_handler_exception(app):
    class CustomException(Exception):
        pass

    @app.get("/foo")
    async def handler(request):
        raise CustomException

    @app.exception(CustomException)
    def handler_exception(request, exception):
        raise Exception

    request, response = app.test_client.get("/foo")
    assert response.status == 500


def test_middleware_exception(app):
    log_stream = StringIO()

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        format="%(message)s", level=logging.DEBUG, stream=log_stream
    )

    @app.middleware(uri="/", attach_to="response")
    async def response_middleware(request, response):
        raise Exception

    @app.route("/foo")
    async def handler(request):  # noqa
        return text("OK")

    request, response = app.test_client.get("/foo")
    assert response.status == 200
    assert (
        "Exception occurred in one of response middleware handlers"
        in log_stream.getvalue()
    )


def test_response_from_request_middleware(app):
    @app.route("/")
    async def root_handler(request):  # noqa
        return text("OK from handler")

    @app.route("/foo/bar")
    async def foobar_handler(request):  # noqa
        return text("OK from handler")

    @app.middleware(attach_to="request")
    async def request_middleware(request):
        return text("OK from middleware")

    request, response = app.test_client.get("/foo/bar")
    assert response.status == 200
    assert response.text == "OK from middleware"

    request, response = app.test_client.get("/")
    assert response.status == 200
    assert response.text == "OK from middleware"


def test_response_from_layered_request_middleware(app):
    @app.route("/")
    async def root_handler(request):  # noqa
        return text("OK from handler")

    @app.route("/foo/bar")
    async def foobar_handler(request):  # noqa
        return text("OK from handler")

    @app.middleware(uri="/foo")
    async def request_middleware(request):
        return text("OK from middleware")

    request, response = app.test_client.get("/foo/bar")
    assert response.status == 200
    assert response.text == "OK from middleware"

    request, response = app.test_client.get("/")
    assert response.status == 200
    assert response.text == "OK from handler"


def test_response_from_response_middleware(app):
    @app.route("/foo")
    async def handler(request):  # noqa
        return text("OK from handler")

    @app.middleware(attach_to="response")
    async def response_middleware(request, response):
        return text("OK from response middleware")

    request, response = app.test_client.get("/foo")
    assert response.status == 200
    assert response.text == "OK from response middleware"


def test_response_from_layered_response_middleware(app):
    @app.route("/")
    async def root_handler(request):  # noqa
        return text("OK from handler")

    @app.route("/foo/bar")
    async def foobar_handler(request):  # noqa
        return text("OK from handler")

    @app.middleware(uri="/foo", attach_to="response")
    def response_middleware(request, response):
        return text("OK from response middleware")

    request, response = app.test_client.get("/foo/bar")
    assert response.status == 200
    assert response.text == "OK from response middleware"

    request, response = app.test_client.get("/")
    assert response.status == 200
    assert response.text == "OK from handler"


def test_response_no_gather(app):
    @app.route("/foo")
    async def handler(request):
        return text("OK from handler")

    response = app.test_client.get("/foo", gather_request=False)
    assert response.status == 200
    assert response.text == "OK from handler"
