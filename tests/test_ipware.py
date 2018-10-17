from sanic.response import text


def test_headers(app):

    # app.config.IPWARE_REQUEST_HEADER_ORDER

    @app.route("/")
    async def handler(request):
        assert request.remote_addr == "177.139.233.139"
        return text(request.remote_addr)

    # test 1
    headers = {
        "X-Forwarded-For": "177.139.233.139, 198.84.193.157, 198.84.193.158"
    }
    request, response = app.test_client.get("/", headers=headers)

    assert response.text == "177.139.233.139"

    # test 2
    headers = {
        "X-Forwarded-For": "177.139.233.139, 198.84.193.157, 198.84.193.158",
        "Forwarded-For": "177.139.233.133",
    }
    request, response = app.test_client.get("/", headers=headers)

    assert response.text == "177.139.233.139"

    # test 3
    app.config.IPWARE_PROXY_TRUSTED_IPS = ["198.84.193.158"]
    headers = {
        "X-Forwarded-For": "177.139.233.139, 198.84.193.157, 198.84.193.158"
    }
    request, response = app.test_client.get("/", headers=headers)

    assert response.text == "177.139.233.139"

    # test 4
    app.config.IPWARE_PROXY_COUNT = 2
    headers = {
        "X-Forwarded-For": "177.139.233.139, 198.84.193.157, 198.84.193.158"
    }
    request, response = app.test_client.get("/", headers=headers)

    assert response.text == "177.139.233.139"


def test_no_running_app(sanic_request):
    assert sanic_request.remote_addr is None
