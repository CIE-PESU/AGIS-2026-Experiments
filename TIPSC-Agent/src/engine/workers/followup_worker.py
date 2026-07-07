class FollowUpWorker:

    def __init__(self, stages):
        self.stages = stages

    def execute(self, tipsc_output, followup_context, compliance_context):
        return self.stages.execute_followup(
            tipsc_output,
            followup_context,
            compliance_context,
        )