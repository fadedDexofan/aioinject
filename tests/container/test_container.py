import contextlib
from collections.abc import AsyncIterator, Iterator

import pytest
from pydantic_settings import BaseSettings

from aioinject import Object, Scoped, Singleton, providers
from aioinject.containers import Container
from aioinject.context import InjectionContext


class _AbstractService:
    pass


class _ServiceA(_AbstractService):
    pass


class _ServiceB(_AbstractService):
    pass


@pytest.fixture
def container() -> Container:
    return Container()


def test_can_init(container: Container) -> None:
    assert container


def test_can_retrieve_context(container: Container) -> None:
    ctx = container.context()
    assert isinstance(ctx, InjectionContext)


def test_can_register_single(container: Container) -> None:
    provider = providers.Scoped(_ServiceA)
    container.register(provider)

    expected = {_ServiceA: [provider]}
    assert container.providers == expected


def test_can_register_batch(container: Container) -> None:
    provider1 = providers.Scoped(_ServiceA)
    provider2 = providers.Scoped(_ServiceB)
    container.register(provider1, provider2)
    excepted = {_ServiceA: [provider1], _ServiceB: [provider2]}
    assert container.providers == excepted


async def test_register_unhashable_implementation(
    container: Container,
) -> None:
    class ExampleSettings(BaseSettings):
        value: list[str] = []

    container.register(Object([], type_=list[int]))
    container.register(Object(ExampleSettings(), type_=ExampleSettings))


def test_cant_register_multiple_providers_for_same_type(
    container: Container,
) -> None:
    container.register(Scoped(int))

    with pytest.raises(
        ValueError,
        match="^Provider for type <class 'int'> with same implementation already registered$",
    ):
        container.register(Scoped(int))


def test_can_try_register(container: Container) -> None:
    def same_impl() -> _ServiceA:
        return _ServiceA()

    provider = providers.Scoped(same_impl, _ServiceA)
    container.register(provider)

    expected = {_ServiceA: [provider]}
    assert container.providers == expected

    container.try_register(providers.Scoped(same_impl, _ServiceA))
    assert container.providers == expected


def test_can_retrieve_single_provider(container: Container) -> None:
    int_provider = providers.Scoped(int)
    container.register(int_provider)
    assert container.get_provider(int)


def test_can_retrieve_multiple_providers(container: Container) -> None:
    int_providers = [
        providers.Scoped(lambda: 1, int),
        providers.Scoped(lambda: 2, int),
    ]
    container.register(*int_providers)
    assert len(container.get_providers(int)) == len(int_providers)


def test_missing_provider() -> None:
    container = Container()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        assert container.get_provider(_ServiceA)

    msg = f"Providers for type {_ServiceA.__qualname__} not found"
    assert str(exc_info.value) == msg


async def test_should_close_singletons() -> None:
    shutdown = False

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal shutdown

        yield 42
        shutdown = True

    container = Container()
    container.register(Singleton(dependency))
    async with container:
        for _ in range(2):
            async with container.context() as ctx:
                assert await ctx.resolve(int) == 42  # noqa: PLR2004

        assert shutdown is False
    assert shutdown is True


def test_should_close_singletons_sync() -> None:
    shutdown = False

    @contextlib.contextmanager
    def dependency() -> Iterator[int]:
        nonlocal shutdown
        yield 42
        shutdown = True

    container = Container()
    container.register(Singleton(dependency))
    with container:
        for _ in range(2):
            with container.sync_context() as ctx:
                assert ctx.resolve(int) == 42  # noqa: PLR2004

        assert shutdown is False
    assert shutdown is True
