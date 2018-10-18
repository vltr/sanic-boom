from sanic.response import text
from sanic.views import HTTPMethodView


def test_simple_method_view(app):
    class TestView(HTTPMethodView):
        def get(self, request, *args, **kwargs):
            return text("OK")

    app.add_route(TestView.as_view(), "/test")

    request, response = app.test_client.get("/test")

    assert response.status == 200
    assert response.text == "OK"
