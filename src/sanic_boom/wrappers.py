from enum import IntEnum


class MiddlewareType(IntEnum):
    REQUEST = 1
    RESPONSE = 2


class Route:
    def __init__(self, name: str, handler: object, methods: set, uri: str):
        self.name = name
        self.handler = handler
        self.methods = methods
        self.uri = uri

    def __repr__(self):
        return "<Route name: {}, methods: {}, uri: {}>".format(
            self.name, self.methods, self.uri
        )


class Middleware:
    def __init__(self, handler: object, attach_to: MiddlewareType):
        self.handler = handler
        self.attach_to = attach_to

    def __repr__(self):
        return "<Middleware for: {}>".format(str(self.attach_to))
