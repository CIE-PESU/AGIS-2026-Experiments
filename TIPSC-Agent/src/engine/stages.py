from pipeline import (
    run_preeval,
    run_validation,
    run_regulatory,
    run_ethics,
    run_tipsc,
    run_followup,
    build_compliance_context,
)


class PipelineStages:

    def __init__(
        self,
        llm,
        agents_cfg,
        task_cfg,
        preeval_skill,
        tipsc_rubric,
        ethics_rubric,
    ):
        self.llm = llm
        self.agents_cfg = agents_cfg
        self.task_cfg = task_cfg
        self.preeval_skill = preeval_skill
        self.tipsc_rubric = tipsc_rubric
        self.ethics_rubric = ethics_rubric


    def execute_preeval(self, preeval_input):
        return run_preeval(
            self.llm,
            self.preeval_skill,
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
            self.ethics_rubric,
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
            self.tipsc_rubric,
            validation_context,
            compliance_context,
            followup_context,
        )
    
    def execute_followup(
        self,
        tipsc_output,
        followup_context,
        compliance_context,
    ):
        return run_followup(
            self.llm,
            tipsc_output,
            self.agents_cfg,
            self.task_cfg,
            followup_context,
            compliance_context,
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