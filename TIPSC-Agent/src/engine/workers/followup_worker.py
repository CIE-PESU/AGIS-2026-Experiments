import asyncio
from engine.workers.base_worker import BaseWorker


class FollowUpWorker(BaseWorker):

    async def execute(self, tipsc_output, followup_context, compliance_context):
        return await asyncio.to_thread(
            self.stages.execute_followup,
            tipsc_output,
            followup_context,
            compliance_context,
        )