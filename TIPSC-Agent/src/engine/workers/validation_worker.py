from engine.workers.base_worker import BaseWorker


class ValidationWorker(BaseWorker):

    def execute(self, preeval):
        return self.stages.execute_validation(preeval)