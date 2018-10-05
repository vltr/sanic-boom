import pytest
from sanic.constants import HTTP_METHODS
from sanic.response import text
from sanic.router import RouteExists


@pytest.mark.parametrize("method", HTTP_METHODS)
def test_versioned_routes_get(app, method, srv_kw):
    method = method.lower()

    func = getattr(app, method)

    if not callable(func):  # noqa
        raise Exception("method {} is not callable on app".format(method))

    @func("/{}".format(method), version=1)
    def handler(request):
        return text("OK")

    client_method = getattr(app.test_client, method)

    request, response = client_method("/v1/{}".format(method), **srv_kw)
    assert response.status == 200


def test_shorthand_routes_get(app, srv_kw):
    @app.get("/get")
    def handler(request):
        return text("OK")

    request, response = app.test_client.get("/get", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.post("/get", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_multiple(app, srv_kw):
    @app.get("/get")
    def get_handler(request):
        return text("OK")

    @app.options("/get")
    def options_handler(request):
        return text("")

    request, response = app.test_client.get("/get/", **srv_kw)
    assert response.status == 200
    assert response.text == "OK"

    request, response = app.test_client.options("/get/", **srv_kw)
    assert response.status == 200

    # there's no strict slashes for mental health
    request, response = app.test_client.get("/get", **srv_kw)
    assert response.status == 200
    assert response.text == "OK"

    request, response = app.test_client.options("/get", **srv_kw)
    assert response.status == 200


def test_route_slashes_overload(app, srv_kw):
    @app.get("/hello/")
    def get_handler(request):
        return text("OK")

    @app.post("/hello/")
    def post_handler(request):
        return text("OK")

    request, response = app.test_client.get("/hello", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/hello/", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.post("/hello", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.post("/hello/", **srv_kw)
    assert response.text == "OK"


def test_shorthand_routes_post(app, srv_kw):
    @app.post("/post")
    def handler(request):
        return text("OK")

    request, response = app.test_client.post("/post", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/post", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_put(app, srv_kw):
    @app.put("/put")
    def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.put("/put", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/put", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_delete(app, srv_kw):
    @app.delete("/delete")
    def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.delete("/delete", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/delete", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_patch(app, srv_kw):
    @app.patch("/patch")
    def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.patch("/patch", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/patch", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_head(app, srv_kw):
    @app.head("/head")
    def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.head("/head", **srv_kw)
    assert response.status == 200

    request, response = app.test_client.get("/head", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_options(app, srv_kw):
    @app.options("/options")
    def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.options("/options", **srv_kw)
    assert response.status == 200

    request, response = app.test_client.get("/options", **srv_kw)
    assert response.status == 405


def test_register_same_route(app):
    @app.get("/hello")
    def first_handler(request):  # noqa
        return text("OK")

    with pytest.raises(RouteExists):

        @app.get("/hello")
        def second_handler(request):
            return text("Not OK")  # noqa


def test_route_not_found(app, srv_kw):
    @app.get("/hello")
    def handler(request):
        return text("OK")  # noqa

    request, response = app.test_client.get("/world", **srv_kw)
    assert response.status == 404


def test_is_stream_handler_warning(app, srv_kw):
    @app.get("/hello")
    def handler(request):
        with pytest.warns(RuntimeWarning):
            assert request.app.router.is_stream_handler(request) is False
        return text("OK")

    request, response = app.test_client.get("/hello", **srv_kw)
    assert response.status == 200


def test_layered_middleware(app, srv_kw):  # 52-59
    pass


def test_blueprint(app, srv_kw):  # 66
    pass


def test_find_route_by_view_name(app, srv_kw):  # 89-92
    pass


def test_route_handler_dot_handler(app, srv_kw):  # 117
    pass
