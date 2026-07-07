from engine.workers.base_worker import BaseWorker


class TIPSCWorker(BaseWorker):

    def execute(
        self,
        preeval,
        validation_context,
        compliance_context,
    ):
        return self.stages.execute_tipsc(
            preeval,
            validation_context,
            compliance_context,
        )