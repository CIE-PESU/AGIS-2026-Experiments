from engine.workers.base_worker import BaseWorker


class PreEvalWorker(BaseWorker):

    def execute(self, preeval_input):
        return self.stages.execute_preeval(preeval_input)