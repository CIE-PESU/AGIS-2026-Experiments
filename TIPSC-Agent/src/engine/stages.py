from pipeline import (
    build_compliance_context,
    run_ethics,
    run_followup,
    run_preeval,
    run_regulatory,
    run_tipsc,
    run_validation,
)


class PipelineStages:
    def __init__(
        self,
        llm,
        agents_cfg,
        task_cfg,
    ):
        self.llm = llm
        self.agents_cfg = agents_cfg
        self.task_cfg = task_cfg

    def execute_preeval(self, preeval_input):
        return run_preeval(
            self.llm,
            preeval_input,
        )

    def execute_validation(self, preeval):
        return run_validation(
            self.llm,
            preeval,
            self.agents_cfg,
            self.task_cfg,
        )

    def execute_regulatory(self, preeval):
        return run_regulatory(
            self.llm,
            preeval,
            self.agents_cfg,
            self.task_cfg,
        )

    def execute_ethics(
        self,
        preeval,
        validation_context,
        regulatory_context,
    ):
        return run_ethics(
            self.llm,
            preeval,
            self.agents_cfg,
            self.task_cfg,
            validation_context,
            regulatory_context,
        )

    def execute_tipsc(
        self,
        preeval,
        validation_context,
        compliance_context,
        followup_context="",
    ):
        return run_tipsc(
            self.llm,
            preeval,
            self.agents_cfg,
            self.task_cfg,
            validation_context,
            compliance_context,
            followup_context,
        )

    def execute_compliance_context(
        self,
        ethics,
        regulatory,
    ):
        return build_compliance_context(
            ethics,
            regulatory,
        )

    def execute_followup(self, tipsc_output, followup_context, compliance_context):
        return run_followup(
            self.llm,
            tipsc_output,
            self.agents_cfg,
            self.task_cfg,
            followup_context=followup_context,
            compliance_context=compliance_context,
        )

    def execute_tipsc_reeval(
        self, preeval, validation_context, compliance_context, followup_context
    ):
        return run_tipsc(
            self.llm,
            preeval,
            self.agents_cfg,
            self.task_cfg,
            validation_context=validation_context,
            compliance_context=compliance_context,
            followup_context=followup_context,
        )
