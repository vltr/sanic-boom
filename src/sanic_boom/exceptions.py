from sanic.exceptions import SanicException


class SanicBoomException(SanicException):
    pass


class NoApplicationFound(SanicBoomException):
    def __init__(
        self,
        message="Resolver.app is None. You should provide an application "
        "instance through the Resolver constructor or the Resolver.app "
        "property",
        **kwargs
    ):
        super().__init__(message, **kwargs)


class InvalidComponent(SanicBoomException):
    def __init__(
        self,
        message="The 'component' parameter expects a subclass of the "
        "Component class",
        **kwargs
    ):
        super().__init__(message, **kwargs)
