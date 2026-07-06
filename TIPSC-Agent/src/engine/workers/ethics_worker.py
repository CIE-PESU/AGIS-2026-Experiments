from engine.workers.base_worker import BaseWorker


class EthicsWorker(BaseWorker):

    def execute(
        self,
        preeval,
        validation_context,
        regulatory_context,
    ):
        return self.stages.execute_ethics(
            preeval,
            validation_context,
            regulatory_context,
        )