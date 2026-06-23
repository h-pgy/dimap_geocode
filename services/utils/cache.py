import time
from collections.abc import Callable
from typing import Any, Generic, TypeVar, overload

T = TypeVar("T")


class TTLCachedProperty(Generic[T]):
    def __init__(self, func: Callable[[Any], T], ttl_seconds: float) -> None:
        self._func = func
        self._ttl = ttl_seconds
        self._attr = f"_ttlcache_{func.__name__}"
        self.__doc__ = func.__doc__

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = f"_ttlcache_{name}"

    @overload
    def __get__(self, instance: None, owner: type) -> "TTLCachedProperty[T]": ...
    @overload
    def __get__(self, instance: object, owner: type) -> T: ...
    def __get__(self, instance: object | None, owner: type) -> "TTLCachedProperty[T] | T":
        if instance is None:
            return self
        agora = time.monotonic()
        cache = instance.__dict__.get(self._attr)
        if cache is not None and cache[1] > agora:
            return cache[0]
        valor = self._func(instance)
        instance.__dict__[self._attr] = (valor, agora + self._ttl)
        return valor


def ttl_cached_property(
    ttl_seconds: float,
) -> Callable[[Callable[[Any], T]], TTLCachedProperty[T]]:
    def decorator(func: Callable[[Any], T]) -> TTLCachedProperty[T]:
        return TTLCachedProperty(func, ttl_seconds)
    return decorator
