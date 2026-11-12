import pytest
from fastmcp import Client

from server import mcp


@pytest.fixture
async def client():
    async with Client(mcp) as c:
        yield c


# TODO(live): first test
