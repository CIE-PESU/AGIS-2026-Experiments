import asyncio
from engine.workers.base_worker import BaseWorker


class TIPSCWorker(BaseWorker):

    async def execute(
        self,
        preeval,
        validation_context,
        compliance_context,
    ):
        return await asyncio.to_thread(
            self.stages.execute_tipsc,
            preeval,
            validation_context,
            compliance_context,
        )