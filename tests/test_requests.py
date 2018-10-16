from sanic.exceptions import ServerError
from sanic.response import text


def test_sync(app):
    @app.route("/")
    def handler(request):
        return text("Hello")

    request, response = app.test_client.get("/")

    assert response.text == "Hello"


def test_remote_address(app):
    @app.route("/")
    def handler(request):
        return text("{}".format(request.ip))

    request, response = app.test_client.get("/")

    assert response.text == "127.0.0.1"


def test_headers(app):
    @app.route("/")
    async def handler(request):
        headers = {"spam": "great"}
        return text("Hello", headers=headers)

    request, response = app.test_client.get("/")

    assert response.headers.get("spam") == "great"


def test_non_str_headers(app):
    @app.route("/")
    async def handler(request):
        headers = {"answer": 42}
        return text("Hello", headers=headers)

    request, response = app.test_client.get("/")

    assert response.headers.get("answer") == "42"


def test_invalid_response(app):
    @app.exception(ServerError)
    def handler_exception(request, exception):
        return text("Internal Server Error.", 500)

    @app.route("/")
    async def handler(request):
        return "This should fail"

    request, response = app.test_client.get("/")
    assert response.status == 500
    assert response.text == "Internal Server Error."
