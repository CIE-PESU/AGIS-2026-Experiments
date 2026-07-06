from concurrent.futures import ThreadPoolExecutor
import logging

from engine.state_machine import PipelineContext, PipelineState

from engine.workers import (
    PreEvalWorker,
    ValidationWorker,
    RegulatoryWorker,
    EthicsWorker,
    TIPSCWorker,
)

logger = logging.getLogger(__name__)

class PipelineExecutor:

    def __init__(self, stages):
        self.stages = stages
        self.preeval_worker = PreEvalWorker(stages)
        self.validation_worker = ValidationWorker(stages)
        self.regulatory_worker = RegulatoryWorker(stages)
        self.ethics_worker = EthicsWorker(stages)
        self.tipsc_worker = TIPSCWorker(stages)

    def run(self, preeval_input):
        
        context = PipelineContext(
            state=PipelineState.PRE_EVAL
        )

        logger.info("Starting Pre-Evaluation")

        context.preeval = self.preeval_worker.execute(preeval_input)

        logger.info("Pre-Evaluation completed")

        logger.info("Launching Validation and Regulatory in parallel")

        context.state = PipelineState.VALIDATION_RUNNING

        #Parallel Start
        with ThreadPoolExecutor(max_workers=2) as executor:

            validation_future = executor.submit(
                self.validation_worker.execute,
                context.preeval,
            )

            regulatory_future = executor.submit(
                self.regulatory_worker.execute,
                context.preeval,
            )
            
            context.state = PipelineState.REGULATORY_RUNNING

            context.validation = validation_future.result()
            logger.info("Validation completed")
            context.regulatory = regulatory_future.result()
            logger.info("Regulatory completed")
        #Parallel End

        validation_context = context.validation.model_dump_json(indent=2)

        regulatory_context = context.regulatory.model_dump_json(indent=2)

        context.state = PipelineState.ETHICS_RUNNING

        logger.info("Starting Ethics")

        context.ethics = self.ethics_worker.execute(
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

        context.tipsc = self.tipsc_worker.execute(
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