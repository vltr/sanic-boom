import inspect
import typing as t

import pytest
from sanic.request import Request

from sanic_boom import Component, Resolver
from sanic_boom.exceptions import InvalidComponent, NoApplicationFound


class JSONBody(t.Generic[t.T_co]):
    pass


class JSONBodyComponent(Component):  # noqa this is a very simple example
    def resolve(self, param: inspect.Parameter) -> bool:
        if hasattr(param.annotation, "__origin__"):
            return param.annotation.__origin__ == JSONBody
        return False

    async def get(self, request: Request, param: inspect.Parameter) -> object:
        return {
            "param_type": param.annotation.__args__[0],
            "param_name": param.name,
        }


class FakeComponent(Component):  # noqa this is a very simple example
    def resolve(self, param: inspect.Parameter) -> bool:
        return False

    async def get(self, request):
        return {}


# --------------------------------------------------------------------------- #
# the perfect world test scenario
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_resolver(some_app, sanic_request):
    async def hello(request, input: JSONBody[str], age: int, accepted: bool):
        return {
            "request": request,
            "input": input,
            "age": age,
            "accepted": accepted,
        }

    some_app.add_component(JSONBodyComponent)

    prefetched = {"age": "22", "accepted": "ok"}
    ret = await some_app.resolver.resolve(
        request=sanic_request, func=hello, prefetched=prefetched
    )

    assert type(ret.get("age")) == int
    assert ret.get("age") == 22
    assert type(ret.get("accepted")) == bool
    assert ret.get("accepted") is True
    assert ret.get("input").get("param_name") == "input"
    assert ret.get("input").get("param_type") == str
    assert ret.get("request") == sanic_request

    ret = await hello(**ret)

    assert type(ret.get("age")) == int
    assert ret.get("age") == 22
    assert type(ret.get("accepted")) == bool
    assert ret.get("accepted") is True
    assert ret.get("input").get("param_name") == "input"
    assert ret.get("input").get("param_type") == str
    assert ret.get("request") == sanic_request

    # testing resolver "cache"
    ret = await some_app.resolver.resolve(
        request=sanic_request, func=hello, prefetched=prefetched
    )
    assert ret is not None


# --------------------------------------------------------------------------- #
# the real world test scenarios
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_resolver_no_components(some_app, sanic_request):
    async def hello(request, input: JSONBody[str]):  # noqa
        pass

    with pytest.raises(ValueError):
        await some_app.resolver.resolve(request=sanic_request, func=hello)


@pytest.mark.asyncio
async def test_resolver_fake_component(some_app, sanic_request):
    async def hello(request, input: JSONBody[str]):  # noqa
        pass

    some_app.add_component(FakeComponent)  # you shall not pass

    with pytest.raises(ValueError):
        await some_app.resolver.resolve(request=sanic_request, func=hello)


def test_resolver_no_app():
    sentinel = object()
    resolver = Resolver()

    assert resolver.app is None

    with pytest.raises(NoApplicationFound):
        resolver.add_component(JSONBodyComponent)

    resolver.app = sentinel
    resolver.add_component(JSONBodyComponent)

    assert resolver.app == sentinel


def test_resolver_wrong_component():
    resolver = Resolver(object())

    with pytest.raises(InvalidComponent):
        resolver.add_component(object)


@pytest.mark.asyncio
async def test_resolver_no_function(sanic_request):
    resolver = Resolver(object())
    resolver.add_component(JSONBodyComponent)

    with pytest.raises(TypeError):
        await resolver.resolve(request=sanic_request, func={})
