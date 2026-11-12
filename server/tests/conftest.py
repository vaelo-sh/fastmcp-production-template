import pytest
from fastmcp import Client

from app.server import create_server
from app.settings import Settings
from app.store import NoteStore


def make_settings(**overrides) -> Settings:
    # _env_file=None: tests never read a developer's .env
    return Settings(_env_file=None, **overrides)


@pytest.fixture
def store() -> NoteStore:
    return NoteStore()


@pytest.fixture
async def client(store):
    async with Client(create_server(make_settings(), store=store)) as c:
        yield c
