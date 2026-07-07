class TIPSCReevalWorker:

    def __init__(self, stages):
        self.stages = stages

    def execute(self, preeval, validation_context, compliance_context, followup_context):
        return self.stages.execute_tipsc_reeval(
            preeval,
            validation_context,
            compliance_context,
            followup_context,
        )