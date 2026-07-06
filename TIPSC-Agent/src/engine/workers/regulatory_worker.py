from engine.workers.base_worker import BaseWorker


class RegulatoryWorker(BaseWorker):

    def execute(self, preeval):
        return self.stages.execute_regulatory(preeval)