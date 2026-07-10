import asyncio
from engine.workers.base_worker import BaseWorker


class ValidationWorker(BaseWorker):

    async def execute(self, preeval):
        return await asyncio.to_thread(
            self.stages.execute_validation, preeval
        )