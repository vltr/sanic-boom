import asyncio
import inspect
import queue
import uuid
from threading import Thread

import pytest
from sanic.request import Request

from sanic_boom import Component, ComponentCache


class NonCached:
    pass


class RequestCached:
    pass


class EndpointCached:
    pass


class ThreadCached:
    pass


class AppCached:
    pass


class NonCachedComponent(Component):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == NonCached

    async def get(self, request: Request, param: inspect.Parameter) -> object:
        return str(uuid.uuid4())


class RequestCachedComponent(NonCachedComponent):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == RequestCached

    def get_cache_lifecycle(self) -> ComponentCache:
        return ComponentCache.REQUEST


class EndpointCachedComponent(NonCachedComponent):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == EndpointCached

    def get_cache_lifecycle(self) -> ComponentCache:
        return ComponentCache.ENDPOINT


class ThreadCachedComponent(NonCachedComponent):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == ThreadCached

    def get_cache_lifecycle(self) -> ComponentCache:
        return ComponentCache.CURRENT_THREAD


class AppCachedComponent(NonCachedComponent):
    def resolve(self, param: inspect.Parameter) -> bool:
        return param.annotation == AppCached

    def get_cache_lifecycle(self) -> ComponentCache:
        return ComponentCache.APP


# --------------------------------------------------------------------------- #
# actual testing
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_non_cached_component(some_app, sanic_request):
    async def hello(my_var: NonCached):
        return my_var

    some_app.add_component(NonCachedComponent)

    kw = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret = await hello(**kw)

    assert type(ret) is str


@pytest.mark.asyncio
async def test_request_cached_component(some_app, sanic_request):
    async def hello(my_var: RequestCached):
        return my_var

    async def world(baz: RequestCached):
        return baz

    some_app.add_component(RequestCachedComponent)

    kw = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret = await hello(**kw)

    assert type(ret) is str
    assert type(sanic_request["_sanic_boom_cache"]) is dict
    assert len(sanic_request["_sanic_boom_cache"]) == 1
    assert ret in sanic_request["_sanic_boom_cache"].values()

    # same request, result should be cached for "my_var"
    kw2 = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret2 = await hello(**kw2)

    assert type(ret2) is str
    assert len(sanic_request["_sanic_boom_cache"]) == 1
    assert ret2 in sanic_request["_sanic_boom_cache"].values()
    # both my_vars should be equal
    assert ret == ret2

    # creating a new request
    new_request = Request(
        url_bytes=b"/foo/baz",
        headers={},
        version=None,
        method="POST",
        transport=None,
    )

    kw3 = await some_app.resolver.resolve(request=new_request, func=hello)
    ret3 = await hello(**kw3)

    assert type(ret3) is str
    assert type(new_request["_sanic_boom_cache"]) is dict
    assert len(new_request["_sanic_boom_cache"]) == 1
    assert ret3 in new_request["_sanic_boom_cache"].values()
    assert ret != ret3

    kw4 = await some_app.resolver.resolve(request=sanic_request, func=world)
    ret4 = await world(**kw4)

    assert ret != ret4


@pytest.mark.asyncio
async def test_endpoint_cached_component(some_app, sanic_request):
    async def hello(my_var: EndpointCached, another_var: EndpointCached):
        return my_var, another_var

    async def world(my_var: EndpointCached):
        return my_var

    some_app.add_component(EndpointCachedComponent)

    kw = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret = await hello(**kw)

    assert type(ret[0]) is str
    assert type(ret[1]) is str
    assert len(some_app.cache_engine._endpoints) == 1
    assert len(some_app.cache_engine._endpoints[hello].values()) == 2
    assert ret[0] in some_app.cache_engine._endpoints[hello].values()
    assert ret[1] in some_app.cache_engine._endpoints[hello].values()

    # same endpoint, result should be cached for "my_var" and "another_var"
    kw2 = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret2 = await hello(**kw2)

    assert len(some_app.cache_engine._endpoints) == 1
    assert ret2[0] in some_app.cache_engine._endpoints[hello].values()
    assert ret2[1] in some_app.cache_engine._endpoints[hello].values()
    # both my_var and another_var should be equal
    assert ret == ret2

    # creating a new request
    new_request = Request(
        url_bytes=b"/foo/baz",
        headers={},
        version=None,
        method="POST",
        transport=None,
    )

    kw3 = await some_app.resolver.resolve(request=new_request, func=hello)
    ret3 = await hello(**kw3)

    # since the cache is bound to the endpoint, the result should be the same
    assert type(ret3[0]) is str
    assert type(ret3[1]) is str
    assert len(some_app.cache_engine._endpoints) == 1
    assert ret3[0] in some_app.cache_engine._endpoints[hello].values()
    assert ret3[1] in some_app.cache_engine._endpoints[hello].values()
    assert ret == ret2
    assert ret == ret3

    # now, with another endpoint
    kw4 = await some_app.resolver.resolve(request=sanic_request, func=world)
    ret4 = await world(**kw4)

    assert type(ret4) is str
    assert len(some_app.cache_engine._endpoints) == 2
    assert ret4 not in some_app.cache_engine._endpoints[hello].values()
    assert ret4 in some_app.cache_engine._endpoints[world].values()
    assert ret[0] != ret4
    assert ret[1] != ret4


@pytest.mark.asyncio
async def test_thread_cached_component_simple(some_app, sanic_request):
    async def hello(my_var: ThreadCached):
        return my_var

    async def world(baz: ThreadCached):
        return baz

    some_app.add_component(ThreadCachedComponent)

    kw = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret = await hello(**kw)

    assert type(ret) is str

    # in the same thread, should be the same value
    kw2 = await some_app.resolver.resolve(request=sanic_request, func=hello)
    ret2 = await hello(**kw2)

    assert type(ret2) is str
    assert len(some_app.cache_engine._thread_local.sanic_boom_cache) == 1
    assert (
        ret2 in some_app.cache_engine._thread_local.sanic_boom_cache.values()
    )
    # both my_vars should be equal
    assert ret == ret2

    # caching the same component, same parameter, different endpoint
    kw3 = await some_app.resolver.resolve(request=sanic_request, func=world)
    ret3 = await world(**kw3)

    assert ret != ret3


@pytest.mark.asyncio
async def test_thread_cached_component_multiple(some_app, sanic_request):
    async def hello(my_var: ThreadCached):
        return my_var

    unique_values = 25
    some_app.add_component(ThreadCachedComponent)
    ret_queue = queue.Queue()

    class SomeThread(Thread):
        def run(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for _ in range(100):
                kw = loop.run_until_complete(
                    some_app.resolver.resolve(
                        request=sanic_request, func=hello
                    )
                )
                ret = loop.run_until_complete(hello(**kw))
                ret_queue.put(ret)

    threads = [SomeThread() for _ in range(unique_values)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    my_vars = [ret_queue.get_nowait() for _ in range(unique_values ** 2)]

    assert len(set(my_vars)) == unique_values


@pytest.mark.asyncio
async def test_app_cached_component(some_app, sanic_request):
    async def hello(my_var: AppCached):
        return my_var

    some_app.add_component(AppCachedComponent)

    ret = None
    ret2 = None

    with pytest.warns(RuntimeWarning):
        kw = await some_app.resolver.resolve(request=sanic_request, func=hello)
        ret = await hello(**kw)

        assert type(ret) is str

    with pytest.warns(RuntimeWarning):
        kw = await some_app.resolver.resolve(request=sanic_request, func=hello)
        ret2 = await hello(**kw)

        assert type(ret2) is str

    assert ret != ret2
