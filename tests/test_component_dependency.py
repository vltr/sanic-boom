import inspect
import json
import typing as t
import uuid
import sys

from sanic.response import text

from sanic_boom import Component, ComponentCache


try:  # noqa
    from ujson import loads as json_loads
except ImportError:  # noqa
    if sys.version_info[:2] == (3, 5):

        def json_loads(data):
            # on Python 3.5 json.loads only supports str not bytes
            return json.loads(data.decode())

    else:
        json_loads = json.loads


class Parser(t.Generic[t.T_co]):
    pass


class BaseParser:  # (metaclass=_ControllerRegister):
    def __init__(self, *, body, track_id):
        self.body = body
        self.track_id = track_id


class JsonParser(BaseParser):
    @property
    def parsed(self):
        return json_loads(self.body)


class BodyComponent(Component):
    def resolve(self, param) -> bool:
        return param.name == "body"

    async def get(self, request, param: inspect.Parameter):
        return request.body

    def get_cache_lifecycle(self):
        return ComponentCache.REQUEST


class TrackerComponent(Component):
    def resolve(self, param) -> bool:
        return param.name == "track_id"

    async def get(self, request, param: inspect.Parameter):
        return str(uuid.uuid4())

    def get_cache_lifecycle(self):
        return ComponentCache.REQUEST


class ParserComponent(Component):
    def resolve(self, param) -> bool:
        try:  # noqa
            return param.annotation.__origin__ == Parser
        except Exception:  # noqa
            return False

    async def get(self, request, param: inspect.Parameter, body, track_id):
        inferred_cls = param.annotation.__args__[0]

        if (
            inspect.isclass(inferred_cls)
            and issubclass(inferred_cls, BaseParser)
        ):  # noqa
            return inferred_cls(body=body, track_id=track_id)
        else:  # noqa
            raise Exception("could not trust the given annotation")

    def get_cache_lifecycle(self):
        return ComponentCache.REQUEST


def test_handler_component(app):
    app.add_component(BodyComponent)
    app.add_component(TrackerComponent)
    app.add_component(ParserComponent)

    @app.post("/")
    async def handler(parser: Parser[JsonParser], track_id):
        assert parser.track_id == track_id
        assert parser.parsed.get("hello") == "world"
        return text("working")

    request, response = app.test_client.post(
        "/", data=json.dumps({"hello": "world"})
    )
    assert response.status == 200
    assert response.text == "working"
