import asyncio
from engine.workers.base_worker import BaseWorker


class RegulatoryWorker(BaseWorker):

    async def execute(self, preeval):
        return await asyncio.to_thread(
            self.stages.execute_regulatory, preeval
        )