import pytest
from sanic.blueprints import Blueprint
from sanic.constants import HTTP_METHODS
from sanic.exceptions import URLBuildError
from sanic.response import text
from sanic.router import RouteExists


@pytest.mark.parametrize("method", HTTP_METHODS)
def test_versioned_routes_get(app, method, srv_kw):
    method = method.lower()

    func = getattr(app, method)

    if not callable(func):  # noqa
        raise Exception("method {} is not callable on app".format(method))

    @func("/{}".format(method), version=1)
    async def handler(request):
        return text("OK")

    client_method = getattr(app.test_client, method)

    request, response = client_method("/v1/{}".format(method), **srv_kw)
    assert response.status == 200


def test_shorthand_routes_get(app, srv_kw):
    @app.get("/get")
    async def handler(request):
        return text("OK")

    request, response = app.test_client.get("/get", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.post("/get", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_multiple(app, srv_kw):
    @app.get("/get")
    async def get_handler(request):
        return text("OK")

    @app.options("/get")
    async def options_handler(request):
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
    async def get_handler(request):
        return text("OK")

    @app.post("/hello/")
    async def post_handler(request):
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
    async def handler(request):
        return text("OK")

    request, response = app.test_client.post("/post", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/post", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_put(app, srv_kw):
    @app.put("/put")
    async def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.put("/put", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/put", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_delete(app, srv_kw):
    @app.delete("/delete")
    async def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.delete("/delete", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/delete", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_patch(app, srv_kw):
    @app.patch("/patch")
    async def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.patch("/patch", **srv_kw)
    assert response.text == "OK"

    request, response = app.test_client.get("/patch", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_head(app, srv_kw):
    @app.head("/head")
    async def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.head("/head", **srv_kw)
    assert response.status == 200

    request, response = app.test_client.get("/head", **srv_kw)
    assert response.status == 405


def test_shorthand_routes_options(app, srv_kw):
    @app.options("/options")
    async def handler(request):
        assert request.stream is None
        return text("OK")

    assert app.is_request_stream is False

    request, response = app.test_client.options("/options", **srv_kw)
    assert response.status == 200

    request, response = app.test_client.get("/options", **srv_kw)
    assert response.status == 405


def test_register_same_route(app):
    @app.get("/hello")
    async def first_handler(request):  # noqa
        return text("OK")

    with pytest.raises(RouteExists):

        @app.get("/hello")
        async def second_handler(request):
            return text("Not OK")  # noqa


def test_route_not_found(app, srv_kw):
    @app.get("/hello")
    async def handler(request):
        return text("OK")  # noqa

    request, response = app.test_client.get("/world", **srv_kw)
    assert response.status == 404


def test_is_stream_handler_warning(app, srv_kw):
    @app.get("/hello")
    async def handler(request):
        with pytest.warns(RuntimeWarning):
            assert request.app.router.is_stream_handler(request) is False
        return text("OK")

    request, response = app.test_client.get("/hello", **srv_kw)
    assert response.status == 200


def test_layered_middleware(app, srv_kw):  # 47-48
    @app.middleware(uri="/hello")
    async def middleware_handler(request):
        request["hello"] = 1

    @app.middleware(uri="/hello", attach_to="response")
    async def middleware_response_handler(request, response):
        request["hello"] += 1

    @app.get("/hello/world")
    async def hello_world_handler(request):
        request["hello"] += 1
        return text("OK")

    @app.route("/foo", methods={"GET"})
    async def foo_handler(request):
        return text("BAR")

    request, response = app.test_client.get("/hello", **srv_kw)
    assert response.status == 404

    request, response = app.test_client.get("/hello/world", **srv_kw)
    assert response.status == 200
    assert response.text == "OK"
    assert request["hello"] == 3

    request, response = app.test_client.get("/foo", **srv_kw)
    assert response.status == 200
    assert response.text == "BAR"
    assert "hello" not in request


def test_blueprint(app, srv_kw):
    bp = Blueprint("test_text", url_prefix="/test")

    @bp.get("/get")
    async def handler(request):
        return text("OK")

    app.blueprint(bp)

    request, response = app.test_client.get("/test/get/", **srv_kw)
    assert response.status == 200

    request, response = app.test_client.get("/test/get", **srv_kw)
    assert response.status == 200


def test_find_route_by_view_name(app, srv_kw):
    bp = Blueprint("test_text", url_prefix="/test")

    @bp.get("/get")
    async def handler(request):
        return text("OK")  # noqa

    app.blueprint(bp)

    assert app.url_for("test_text.handler") == "/test/get"

    with pytest.raises(URLBuildError):
        app.url_for("foobarbaz")

    with pytest.raises(URLBuildError):
        app.url_for(None)


def test_error_on_same_variable_names(app, srv_kw):
    with pytest.raises(ValueError):

        @app.get("/hello/:variable/:variable")
        async def handler(request):  # noqa
            pass

    with pytest.raises(ValueError):

        @app.get("/hello/:variable/*variable")
        async def another_handler(request):  # noqa
            pass


def test_variable_name_substitution(app, srv_kw):
    @app.get("/get/:command/:id/*src")
    async def handler(request):  # noqa
        pass

    assert (
        app.url_for("handler", command="details", id=20, src="my/favicon.ico")
        == "/get/details/20/my/favicon.ico"
    )

    with pytest.raises(URLBuildError):
        app.url_for("handler", command="details", src="my/favicon.ico")

    with pytest.raises(URLBuildError):
        app.url_for("handler", command="details", id=20)

    with pytest.raises(URLBuildError):
        app.url_for("handler", command="details", id=20, src="foo:bar")


def test_possible_values_on_methods(app):
    @app.route("/", methods=None)
    async def handler(request):
        return text("OK")  # noqa

    assert app.router.get_supported_methods("/") == {"GET"}

    @app.route("/hello", methods="GET")
    async def hello_handler(request):
        return text("OK")  # noqa

    assert app.url_for("hello_handler") == "/hello"
    assert app.router.get_supported_methods("/hello") == {"GET"}

    @app.route("/world", methods=("GET", "POST"))
    async def world_handler(request):
        return text("OK")  # noqa

    assert app.router.get_supported_methods("/world") == {"GET", "POST"}

    with pytest.raises(ValueError):

        @app.route("/foo", methods=range)
        async def range_handler(request):
            return text("OK")  # noqa


def test_duplicate_name_for_handlers(app):
    @app.get("/", name="foo")
    async def foo_root_handler(request):
        return text("OK")  # noqa

    with pytest.raises(RouteExists):

        @app.get("/foo", name="foo")
        async def foo_handler(request):
            return text("OK")  # noqa


def test_basic_component_handling(app, srv_kw):
    @app.get("/test/:command/:identifier")
    async def handler(command: str, identifier: int):
        assert isinstance(command, str)
        assert command == "error"
        assert isinstance(identifier, int)
        assert identifier == 42
        return text("OK")

    request, response = app.test_client.get("/test/error/42", **srv_kw)
    assert response.status == 200
