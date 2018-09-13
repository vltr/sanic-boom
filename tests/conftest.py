import pytest
from sanic.request import Request

from sanic_boom import CacheEngine
from sanic_boom import Component
from sanic_boom import Resolver
from sanic_boom import param_parser


class SomeApp:
    """Just a simple mock of the Sanic app that I pretend to evolve in the near
    future.
    """

    def __init__(self):
        self.param_parser = param_parser
        self.resolver = Resolver(self)
        self.cache_engine = CacheEngine(self)

    def add_component(self, component: Component):
        self.resolver.add_component(component)


@pytest.fixture
def sanic_request():
    return Request(
        url_bytes=b"/foo/bar",
        headers={},
        version=None,
        method="GET",
        transport=None,
    )


@pytest.fixture
def some_app():
    return SomeApp()
