"""Integration fixtures: a real MongoDB (single-node replica set) via
testcontainers, matching production topology (C-1). These tests are
skipped automatically when Docker isn't available in the environment —
`pytest.importorskip`/container startup failures degrade to a skip rather
than a hard failure, so `pytest tests/unit` always works standalone."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="testcontainers not installed")

from testcontainers.mongodb import MongoDbContainer  # noqa: E402


@pytest.fixture(scope="session")
def mongo_container():
    try:
        with MongoDbContainer("mongo:7").with_command(
            "mongod --replSet rs0 --bind_ip_all"
        ) as container:
            client = container.get_connection_client()
            client.admin.command("replSetInitiate", {"_id": "rs0", "members": [{"_id": 0, "host": "localhost:27017"}]})
            yield container
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Docker/testcontainers unavailable: {exc}")


@pytest_asyncio.fixture
async def db(mongo_container):
    from motor.motor_asyncio import AsyncIOMotorClient

    uri = mongo_container.get_connection_url()
    client = AsyncIOMotorClient(uri)
    database = client["finance_tracker_test"]
    from app.db import ensure_indexes

    await ensure_indexes(database)
    yield database
    await client.drop_database("finance_tracker_test")
    client.close()
