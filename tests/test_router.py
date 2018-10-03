import pytest
from sanic.constants import HTTP_METHODS
from sanic.response import text


@pytest.mark.parametrize("method", HTTP_METHODS)
def test_versioned_routes_get(boom_app, method, server_kw):
    method = method.lower()

    func = getattr(boom_app, method)

    if not callable(func):
        raise Exception("method {} is not callable on app".format(method))

    @func("/{}".format(method), version=1)
    def handler(request):
        return text("OK")

    client_method = getattr(boom_app.test_client, method)

    request, response = client_method(
        "/v1/{}".format(method), server_kwargs=server_kw
    )
    assert response.status == 200


def test_shorthand_routes_get(boom_app, server_kw):
    @boom_app.get("/get")
    def handler(request):
        return text("OK")

    request, response = boom_app.test_client.get(
        "/get", server_kwargs=server_kw
    )
    assert response.text == "OK"

    request, response = boom_app.test_client.post(
        "/get", server_kwargs=server_kw
    )
    assert response.status == 405
