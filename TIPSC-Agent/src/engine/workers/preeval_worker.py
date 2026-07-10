import asyncio
from engine.workers.base_worker import BaseWorker


class PreEvalWorker(BaseWorker):

    async def execute(self, preeval_input):
        return await asyncio.to_thread(
            self.stages.execute_preeval, preeval_input
        )