import asyncio
from engine.workers.base_worker import BaseWorker


class TIPSCReevalWorker(BaseWorker):

    async def execute(self, preeval, validation_context, compliance_context, followup_context):
        return await asyncio.to_thread(
            self.stages.execute_tipsc_reeval,
            preeval,
            validation_context,
            compliance_context,
            followup_context,
        )