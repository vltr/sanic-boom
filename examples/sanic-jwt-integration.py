from sanic.response import text
from sanic_jwt import Initialize, exceptions

from sanic_boom import Component, ComponentCache, SanicBoom

# --------------------------------------------------------------------------- #
# sanic-jwt related code
# --------------------------------------------------------------------------- #


class User(object):
    def __init__(self, id, username, password):
        self.user_id = id
        self.username = username
        self.password = password

    def __str__(self):
        return "User(id='{}')".format(self.id)

    def to_dict(self):
        return {"user_id": self.user_id, "username": self.username}


users = [
    User(1, "user1", "abcxyz"),
    User(2, "user2", "abcxyz"),
    User(3, "user3", "abcxyz"),
    User(4, "user4", "abcxyz"),
]

username_table = {u.username: u for u in users}
userid_table = {u.user_id: u for u in users}


async def authenticate(request, *args, **kwargs):
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    if not username or not password:
        raise exceptions.AuthenticationFailed("Missing username or password.")

    user = username_table.get(username, None)
    if user is None:
        raise exceptions.AuthenticationFailed("User not found.")

    if password != user.password:
        raise exceptions.AuthenticationFailed("Password is incorrect.")

    return user


# --------------------------------------------------------------------------- #
# sanic-boom related code
# --------------------------------------------------------------------------- #


class AuthComponent(Component):  # for shorthand
    def resolve(self, param) -> bool:
        return param.name == "auth"

    async def get(self, request, param):
        return request.app.auth


class JWTComponent(Component):
    def resolve(self, param) -> bool:
        return param.name == "jwt_user_id"

    async def get(self, request, param, auth):  # component inter-dependency
        is_valid, status, reasons = auth._check_authentication(
            request, None, None
        )
        if not is_valid:
            raise exceptions.Unauthorized(reasons, status_code=status)
        return auth.extract_user_id(request)

    def get_cache_lifecycle(self):
        return ComponentCache.REQUEST


app = SanicBoom(__name__)
sanicjwt = Initialize(app, authenticate=authenticate)

# adding components
app.add_component(AuthComponent)
app.add_component(JWTComponent)


@app.middleware(uri="/restricted")
async def restricted_middleware(jwt_user_id):
    pass  # this is really it!


@app.get("/restricted/foo")
async def restricted_handler(jwt_user_id):
    return text(jwt_user_id)


@app.get("/restricted/bar")
async def another_restricted_handler():
    return text("this is restricted!")


@app.get("/")
async def unrestricted_handler():
    return text("OK")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, workers=1)
