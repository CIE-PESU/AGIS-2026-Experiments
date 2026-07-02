import logging
# from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class PipelineExecutor:

    def __init__(self, stages):
        self.stages = stages

    def run(self, preeval_input):
        
        logger.info("Starting Pre-Evaluation")

        preeval = self.stages.execute_preeval(preeval_input)

        logger.info("Pre-Evaluation completed")

        logger.info("Launching Validation and Regulatory in parallel")

        #Parallel Start
        # with ThreadPoolExecutor(max_workers=2) as executor:

        #     validation_future = executor.submit(
        #         self.stages.execute_validation,
        #         preeval,
        #     )

        #     regulatory_future = executor.submit(
        #         self.stages.execute_regulatory,
        #         preeval,
        #     )

        #     validation = validation_future.result()
        #     logger.info("Validation completed")
        #     regulatory = regulatory_future.result()
        #     logger.info("Regulatory completed")
        # #Parallel End

        # validation_context = validation.model_dump_json(indent=2)

        # regulatory_context = regulatory.model_dump_json(indent=2)

        validation = self.stages.execute_validation(preeval)
        validation_context = validation.model_dump_json(indent=2)

        regulatory = self.stages.execute_regulatory(preeval)
        regulatory_context = regulatory.model_dump_json(indent=2)


        logger.info("Starting Ethics")

        ethics = self.stages.execute_ethics(
            preeval,
            validation_context,
            regulatory_context,
        )

        logger.info("Ethics completed")

        compliance_context = self.stages.execute_compliance_context(
            ethics,
            regulatory,
        )

        logger.info("Starting TIPSC")

        tipsc = self.stages.execute_tipsc(
            preeval,
            validation_context,
            compliance_context,
        )

        logger.info("TIPSC completed")

        return {
            "preeval": preeval,
            "validation": validation,
            "regulatory": regulatory,
            "ethics": ethics,
            "tipsc": tipsc,
            "compliance_context": compliance_context,
        }