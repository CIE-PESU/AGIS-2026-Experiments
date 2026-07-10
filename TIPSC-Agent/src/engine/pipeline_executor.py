import asyncio
import logging
from engine.dispatcher import WorkerDispatcher
from engine.state_machine import PipelineContext, PipelineState

logger = logging.getLogger(__name__)


class PipelineExecutor:

    def __init__(self, stages):
        self.stages = stages
        self.dispatcher = WorkerDispatcher(stages)

    async def run(self, preeval_input):

        context = PipelineContext(
            state=PipelineState.PRE_EVAL
        )

        logger.info("Starting Pre-Evaluation")

        context.preeval = await self.dispatcher.dispatch_preeval(preeval_input)

        logger.info("Pre-Evaluation completed")

        logger.info("Launching Validation and Regulatory in parallel")

        context.state = PipelineState.VALIDATION_RUNNING

        context.validation, context.regulatory = await asyncio.gather(
            self.dispatcher.dispatch_validation(context.preeval),
            self.dispatcher.dispatch_regulatory(context.preeval),
        )

        context.state = PipelineState.REGULATORY_RUNNING
        logger.info("Validation completed")
        logger.info("Regulatory completed")

        validation_context = context.validation.model_dump_json(indent=2)
        regulatory_context = context.regulatory.model_dump_json(indent=2)

        context.state = PipelineState.ETHICS_RUNNING

        logger.info("Starting Ethics")
        context.ethics = await self.dispatcher.dispatch_ethics(
            context.preeval,
            validation_context,
            regulatory_context,
        )
        logger.info("Ethics completed")

        context.compliance_context = self.stages.execute_compliance_context(
            context.ethics,
            context.regulatory,
        )

        context.state = PipelineState.TIPSC_RUNNING

        logger.info("Starting TIPSC")

        context.tipsc = await self.dispatcher.dispatch_tipsc(
            context.preeval,
            validation_context,
            context.compliance_context,
        )
        logger.info("TIPSC completed")

        context.state = PipelineState.TIPSC_COMPLETE

        return {
            "preeval": context.preeval,
            "validation": context.validation,
            "regulatory": context.regulatory,
            "ethics": context.ethics,
            "tipsc": context.tipsc,
            "compliance_context": context.compliance_context,
            "state": context.state,
        }