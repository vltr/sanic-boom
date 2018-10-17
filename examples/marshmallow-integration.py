"""Example code taken from
https://marshmallow.readthedocs.io/en/3.0/quickstart.html#quickstart
"""

import datetime as dt
import inspect
import typing as t

from marshmallow import Schema, fields, post_load
from sanic.exceptions import ServerError
from sanic.response import text

from sanic_boom import Component, SanicBoom

# --------------------------------------------------------------------------- #
# marshmallow related code
# --------------------------------------------------------------------------- #


class User(object):
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.created_at = dt.datetime.now()

    def __repr__(self):
        return "<User(name={self.name!r})>".format(self=self)

    def say_hi(self):
        return "hi, my name is {}".format(self.name)


class UserSchema(Schema):
    name = fields.Str()
    email = fields.Email()
    created_at = fields.DateTime()

    @post_load
    def make_user(self, data):
        return User(**data)


# --------------------------------------------------------------------------- #
# sanic-boom related code
# --------------------------------------------------------------------------- #


class JSONBody(t.Generic[t.T_co]):
    pass


class JSONBodyComponent(Component):
    def resolve(self, param: inspect.Parameter) -> bool:
        if hasattr(param.annotation, "__origin__"):
            return param.annotation.__origin__ == JSONBody
        return False

    async def get(self, request, param: inspect.Parameter) -> object:
        inferred_type = param.annotation.__args__[0]
        try:
            return inferred_type().load(request.json).data
        except Exception:
            raise ServerError(
                "Couldn't convert JSON body to {!s}".format(inferred_type)
            )


app = SanicBoom(__name__)
app.add_component(JSONBodyComponent)


@app.post("/")
async def handler(user: JSONBody[UserSchema]):  # notice the handler parameters
    return text(user.say_hi())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, workers=1)


# then, run:
# curl -v http://localhost:8000/ -d '{"name":"John Doe","email":"john.doe@example.tld"}'
