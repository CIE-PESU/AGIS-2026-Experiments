"""
tests/integration/test_full_flow.py — End-to-end integration test skeleton.

Requires Docker (for testcontainers-python) and a running instance of:
    - MongoDB
    - Kafka

Run with:
    pytest backend/tests/integration/ --timeout=120 -m integration

Install extras:
    pip install testcontainers pytest-asyncio httpx
"""

import pytest

# ---------------------------------------------------------------------------
# Fixtures (to be implemented when testcontainers are wired)
# ---------------------------------------------------------------------------

# @pytest.fixture(scope="module")
# async def test_mongo():
#     """Spin up a MongoDB testcontainer."""
#     from testcontainers.mongodb import MongoDbContainer
#     with MongoDbContainer("mongo:7") as mongo:
#         yield mongo.get_connection_url()


# @pytest.fixture(scope="module")
# async def test_kafka():
#     """Spin up a Kafka testcontainer."""
#     from testcontainers.kafka import KafkaContainer
#     with KafkaContainer() as kafka:
#         yield kafka.get_bootstrap_server()


# @pytest.fixture(scope="module")
# async def test_client(test_mongo, test_kafka):
#     """ASGI test client connected to real containers."""
#     import os
#     os.environ["MONGODB_URI"] = test_mongo
#     os.environ["KAFKA_BOOTSTRAP_SERVERS"] = test_kafka
#     from httpx import AsyncClient, ASGITransport
#     from main import create_app
#     app = create_app()
#     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
#         yield client


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skip(reason="Requires Docker + testcontainers — run manually in CI")
async def test_session_create_triggers_tipsc():
    """
    Full flow: POST /sessions → status=queued → TIPSC runs → status=tipsc_completed.

    Steps:
      1. Create a session with valid problem_statement and idea
      2. Poll GET /sessions/{id} until status != "queued"
      3. Assert status is "tipsc_completed" or "waiting_for_founder"
    """
    # TODO: implement with testcontainers fixtures when CI is ready
    pass


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Docker + testcontainers — run manually in CI")
async def test_tipsc_to_dfv_to_discovery():
    """
    Full end-to-end flow through all three stages:
      TIPSC completed → DFV triggered → DFV completed → Discovery triggered → completed
    """
    # TODO: implement with testcontainers fixtures
    pass


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Docker + testcontainers — run manually in CI")
async def test_followup_resumption():
    """
    If TIPSC sets waiting_for_founder:
      POST /sessions/user/{student_id}/followup → TIPSC resumes → tipsc_completed
    """
    # TODO: implement with testcontainers fixtures
    pass
