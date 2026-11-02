"""Notification updates must never create a new session document."""

from bson import ObjectId
import pytest

from workers.notification_worker import NotificationWorker


class Collection:
    def __init__(self):
        self.update_args = None

    async def find_one(self, query):
        return None

    async def update_one(self, *args, **kwargs):
        self.update_args = (args, kwargs)
        return type("Result", (), {"modified_count": 1})()


@pytest.mark.asyncio
async def test_notification_uses_object_id_and_never_upserts():
    worker = NotificationWorker()
    collection = Collection()
    worker.db = {"sessions": collection}
    session_id = str(ObjectId())
    await worker._handle_message({
        "userSession_id": session_id,
        "correlation_id": "current-run",
        "flow": "dfv",
        "status": "done",
    })
    args, kwargs = collection.update_args
    assert args[0]["_id"] == ObjectId(session_id)
    assert args[0]["correlation_id"] == "current-run"
    assert kwargs["upsert"] is False


@pytest.mark.asyncio
async def test_invalid_flow_cannot_become_mongo_field():
    worker = NotificationWorker()
    collection = Collection()
    worker.db = {"sessions": collection}
    await worker._handle_message({
        "userSession_id": str(ObjectId()),
        "correlation_id": "current-run",
        "flow": "bad.field",
        "status": "done",
    })
    assert collection.update_args is None
