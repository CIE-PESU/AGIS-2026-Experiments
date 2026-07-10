from engine.workers import (
    PreEvalWorker,
    ValidationWorker,
    RegulatoryWorker,
    EthicsWorker,
    TIPSCWorker,
    FollowUpWorker,
    TIPSCReevalWorker,
)


class WorkerDispatcher:

    def __init__(self, stages):
        self.preeval_worker = PreEvalWorker(stages)
        self.validation_worker = ValidationWorker(stages)
        self.regulatory_worker = RegulatoryWorker(stages)
        self.ethics_worker = EthicsWorker(stages)
        self.tipsc_worker = TIPSCWorker(stages)
        self.followup_worker = FollowUpWorker(stages)
        self.tipsc_reeval_worker = TIPSCReevalWorker(stages)

    async def dispatch_preeval(self, preeval_input):
        return await self.preeval_worker.execute(preeval_input)

    async def dispatch_validation(self, preeval):
        return await self.validation_worker.execute(preeval)

    async def dispatch_regulatory(self, preeval):
        return await self.regulatory_worker.execute(preeval)

    async def dispatch_ethics(self, preeval, validation_context, regulatory_context):
        return await self.ethics_worker.execute(
            preeval, validation_context, regulatory_context
        )

    async def dispatch_tipsc(self, preeval, validation_context, compliance_context, followup_context=""):
        return await self.tipsc_worker.execute(
            preeval, validation_context, compliance_context
        )

    async def dispatch_followup(self, tipsc_output, followup_context, compliance_context):
        return await self.followup_worker.execute(
            tipsc_output, followup_context, compliance_context
        )

    async def dispatch_tipsc_reeval(self, preeval, validation_context, compliance_context, followup_context):
        return await self.tipsc_reeval_worker.execute(
            preeval, validation_context, compliance_context, followup_context
        )
    
