import inspect
import typing as t
from functools import lru_cache

from sanic.log import logger
from sanic.request import Request

from sanic_boom.component import Component
from sanic_boom.exceptions import InvalidComponent, NoApplicationFound


class Resolver:
    def __init__(self, app=None):
        self.app = app
        self.components = []

    def add_component(self, component: Component):
        if self.app is None:
            raise NoApplicationFound()
        if not issubclass(component, Component):
            raise InvalidComponent()

        self.components.append(component(self.app))

    @lru_cache(maxsize=768)
    def find_component(self, *, param: inspect.Parameter) -> Component:
        for component in self.components:
            resolved = component.resolve(param)
            if resolved:
                return component
        return None

    async def resolve(
        self,
        *,
        request: Request,
        func: t.Callable,
        prefetched: t.Dict[str, t.Any] = None,
        source_param: inspect.Parameter = None
    ) -> t.Dict[str, t.Any]:
        if not inspect.isfunction(func) and not inspect.iscoroutinefunction(
            func
        ):
            raise TypeError('The provided parameter "func" is not a function')
        kwargs = {}
        params = inspect.signature(func).parameters

        for param in params.values():

            if prefetched is not None and param.name in prefetched:
                kwargs.update(
                    {
                        param.name: self.app.param_parser(
                            prefetched.get(param.name), param
                        )
                    }
                )
                continue

            if isinstance(param.annotation, Request) or param.name in (
                "request",
                "req",
            ):
                kwargs.update({param.name: request})
                continue

            if isinstance(
                param.annotation, inspect.Parameter
            ) or param.name in ("param", "parameter"):
                kwargs.update({param.name: source_param or param})
                continue

            if param.kind == param.VAR_POSITIONAL:  # equals *args, *a
                # this is only valid for HTTPMethodView
                if hasattr(func, "view_class"):
                    # most likely request is the only thing missing here
                    kwargs.update({"request": request})
                else:
                    logger.debug(
                        "Parameter '{}' skipped from resolver".format(
                            param.name
                        )
                    )
                continue

            elif param.kind == param.VAR_KEYWORD:  # equals **kw, **kwargs
                logger.debug(
                    "Parameter '{}' skipped from resolver".format(param.name)
                )
                continue

            component = self.find_component(param=param)

            if component is None:
                raise ValueError(
                    'The requested parameter "{}" could not be resolved to a '
                    "component".format(param.name)
                )
            else:
                value = await self.app.cache_engine.get(
                    component, func, request, source_param or param
                )
                kwargs.update({param.name: value})

        return kwargs


__all__ = ("Resolver",)
