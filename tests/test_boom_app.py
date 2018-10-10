import inspect

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


def test_prepend_slash(app, srv_kw):
    @app.get("foo")
    async def handler(request):
        return text("OK")

    request, response = app.test_client.get("/foo", **srv_kw)
    assert response.status == 200
    assert response.text == "OK"
