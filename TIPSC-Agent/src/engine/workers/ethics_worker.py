import asyncio
from engine.workers.base_worker import BaseWorker


class EthicsWorker(BaseWorker):

    async def execute(
        self,
        preeval,
        validation_context,
        regulatory_context,
    ):
        return await asyncio.to_thread(
            self.stages.execute_ethics,
            preeval,
            validation_context,
            regulatory_context,
        )