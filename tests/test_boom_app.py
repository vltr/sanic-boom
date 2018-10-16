import asyncio
import inspect

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


def test_response_timeout(app):

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
