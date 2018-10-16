import inspect
import json
import typing as t
import uuid

from sanic.response import text

from sanic_boom import Component, ComponentCache


class JSONBody:
    pass


class Headers:
    pass


class RequestIdentifier:
    pass


class ComplexJSONBody(t.Generic[t.T_co]):
    pass


class JSONBodyComponent(Component):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == JSONBody

    async def get(self, request, param: inspect.Parameter) -> object:
        return request.json


class HeaderComponent(Component):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == Headers

    async def get(self, request, param: inspect.Parameter) -> object:
        return request.headers


class ComplexJSONBodyComponent(Component):
    def resolve(self, param: inspect.Parameter) -> bool:
        if hasattr(param.annotation, "__origin__"):
            return param.annotation.__origin__ == ComplexJSONBody
        return False

    async def get(self, request, param: inspect.Parameter) -> object:
        inferred_type = param.annotation.__args__[0]
        return inferred_type(**request.json)


class RequestIdentifierComponent(Component):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == RequestIdentifier

    async def get(self, request, param: inspect.Parameter) -> object:
        return str(uuid.uuid4())

    def get_cache_lifecycle(self) -> ComponentCache:
        return ComponentCache.REQUEST


def test_handler_component(app):
    app.add_component(JSONBodyComponent)

    @app.post("/")
    async def handler(body: JSONBody):
        return text(body.get("hello"))

    request, response = app.test_client.post(
        "/", data=json.dumps({"hello": "world"})
    )
    assert response.status == 200
    assert response.text == "world"


def test_middleware_component(app):
    app.add_component(HeaderComponent)
    some_uuid = str(uuid.uuid4())

    @app.middleware  # global
    async def req_middleware(headers: Headers):
        headers["uuid"] = some_uuid

    @app.middleware(
        attach_to="response"
    )  # ! this needs to be checked # global
    async def resp_middleware(headers: Headers):
        assert "uuid" in headers

    @app.get("/uuid")
    async def handler(headers: Headers):
        return text(headers.get("uuid"))

    request, response = app.test_client.get("/uuid")
    assert response.status == 200
    assert response.text == some_uuid


def test_complex_component(app):
    class TestBody:
        def __init__(self, name=None, age=None):
            self.name = name
            self.age = age

        def say_hi(self):
            return "{}, aged {}, says hi".format(self.name, self.age)

    app.add_component(ComplexJSONBodyComponent)
    app.add_component(HeaderComponent)

    @app.post("/")
    async def handler(
        request, headers: Headers, complex_body: ComplexJSONBody[TestBody]
    ):
        assert request.headers == headers
        assert isinstance(complex_body, TestBody)
        assert complex_body.name == "John"
        assert complex_body.age == 42
        return text(complex_body.say_hi())

    request, response = app.test_client.post(
        "/", data=json.dumps({"name": "John", "age": 42})
    )
    assert response.status == 200
    assert response.text == "John, aged 42, says hi"


def test_cached_component(app):

    app.add_component(RequestIdentifierComponent)

    @app.middleware  # global
    async def req_middleware(request, req_uuid: RequestIdentifier):
        request[req_uuid] = 1

    @app.get("/uuid")
    async def handler(request, req_uuid: RequestIdentifier):
        request[req_uuid] += 1
        return text(req_uuid)

    request, response = app.test_client.get("/uuid")
    assert response.status == 200
    assert request[response.text] == 2

    # the cache is only valid for the request lifecycle
    request, response = app.test_client.get("/uuid")
    assert response.status == 200
    assert request[response.text] == 2
