==============
``sanic-boom``
==============

.. start-badges

.. image:: https://img.shields.io/pypi/status/sanic-boom.svg
    :alt: PyPI - Status
    :target: https://pypi.org/project/sanic-boom/

.. image:: https://img.shields.io/pypi/v/sanic-boom.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/sanic-boom/

.. image:: https://img.shields.io/pypi/pyversions/sanic-boom.svg
    :alt: Supported versions
    :target: https://pypi.org/project/sanic-boom/

.. image:: https://travis-ci.org/vltr/sanic-boom.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/vltr/sanic-boom

.. image:: https://readthedocs.org/projects/sanic-boom/badge/?style=flat
    :target: https://readthedocs.org/projects/sanic-boom
    :alt: Documentation Status

.. image:: https://codecov.io/github/vltr/sanic-boom/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/vltr/sanic-boom

.. image:: https://api.codacy.com/project/badge/Grade/633a45702c6c43a3815ed7199a0be7b2
    :alt: Codacy Grade
    :target: https://www.codacy.com/app/vltr/sanic-boom?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=vltr/sanic-boom&amp;utm_campaign=Badge_Grade

.. image:: https://pyup.io/repos/github/vltr/sanic-boom/shield.svg
    :target: https://pyup.io/account/repos/github/vltr/sanic-boom/
    :alt: Packages status

.. end-badges

Components injection, fast routing and non-global (layered) middlewares. Give your Sanic application a Boom!

In a nutshell
-------------

.. code-block:: python

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

::

    $ curl -v http://localhost:8000/ -d '{"name":"John Doe","email":"john.doe@example.tld"}'
    *   Trying ::1...
    * TCP_NODELAY set
    * connect to ::1 port 8000 failed: Connection refused
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to localhost (127.0.0.1) port 8000 (#0)
    > POST / HTTP/1.1
    > Host: localhost:8000
    > User-Agent: curl/7.61.1
    > Accept: */*
    > Content-Length: 50
    > Content-Type: application/x-www-form-urlencoded
    >
    * upload completely sent off: 50 out of 50 bytes
    < HTTP/1.1 200 OK
    < Connection: keep-alive
    < Keep-Alive: 5
    < Content-Length: 23
    < Content-Type: text/plain; charset=utf-8
    <
    * Connection #0 to host localhost left intact
    hi, my name is John Doe

.. warning::

    **IMPORTANT**: ``sanic-boom`` is in **very early stages** of development! Use with caution and be aware that some functionalities and APIs may change between versions until they're out of **alpha**.

Dependencies
============

``sanic-boom`` depends on two "not-so-known" libraries (both created by the author of ``sanic-boom``):

- `sanic-ipware <https://github.com/vltr/sanic-ipware>`_; and
- `xrtr <https://xrtr.readthedocs.io/en/latest/>`_

.. important::

    Since ``xrtr`` **replaces** the Sanic default router under the hood in ``sanic-boom``, it is very important for the developer to read its documentation (in the link provided above).

Documentation
=============

https://sanic-boom.readthedocs.io/en/latest/

License
=======

``sanic-boom`` is a free software distributed under the `MIT <https://choosealicense.com/licenses/mit/>`_ license.
