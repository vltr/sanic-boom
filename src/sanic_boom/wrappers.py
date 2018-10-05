# class Handler:
#     def __init__(self, endpoint: object, middlewares: list):
#         self.endpoint = endpoint
#         self.middlewares = middlewares


class Route:
    def __init__(self, name: str, handler: object, methods: set, uri: str):
        self.name = name
        self.handler = handler
        self.methods = methods
        self.uri = uri


class Middleware:
    def __init__(
        self, handler: object, methods: set, uri: str, attach_to: str
    ):
        self.handler = handler
        self.methods = methods
        self.uri = uri
        self.attach_to = attach_to
