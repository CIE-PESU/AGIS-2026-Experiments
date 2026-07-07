import os

from engine.kafka import (
    MessageProducer,
    KafkaTopics,
)

from engine.workers import (
    PreEvalWorker,
    ValidationWorker,
    RegulatoryWorker,
    EthicsWorker,
    TIPSCWorker,
    FollowUpWorker,
    TIPSCReevalWorker,
)


class WorkerDispatcher:

    def __init__(self, stages):

        self.use_kafka = (
            os.getenv("USE_KAFKA", "false").lower() == "true"
        )

        self.producer = MessageProducer()

        self.preeval_worker = PreEvalWorker(stages)
        self.validation_worker = ValidationWorker(stages)
        self.regulatory_worker = RegulatoryWorker(stages)
        self.ethics_worker = EthicsWorker(stages)
        self.tipsc_worker = TIPSCWorker(stages)
        self.followup_worker = FollowUpWorker(stages)         
        self.tipsc_reeval_worker = TIPSCReevalWorker(stages)  

    def dispatch_preeval(self, *args):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.PRE_EVAL, args)
            return None
        return self.preeval_worker.execute(*args)

    def dispatch_validation(self, preeval):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.VALIDATION, preeval)
            return None
        return self.validation_worker.execute(preeval)

    def dispatch_regulatory(self, preeval):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.REGULATORY, preeval)
            return None
        return self.regulatory_worker.execute(preeval)

    def dispatch_ethics(self, preeval, validation_context, regulatory_context):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.ETHICS, ...)
            return None
        return self.ethics_worker.execute(preeval, validation_context, regulatory_context)

    def dispatch_tipsc(self, preeval, validation_context, compliance_context):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.TIPSC, ...)
            return None
        return self.tipsc_worker.execute(preeval, validation_context, compliance_context)
    
    def dispatch_followup(self, tipsc_output, followup_context, compliance_context):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.FOLLOWUP, ...)
            return None
        return self.followup_worker.execute(
            tipsc_output,
            followup_context,
            compliance_context,
        )

    def dispatch_tipsc_reeval(self, preeval, validation_context, compliance_context, followup_context):
        if self.use_kafka:
            self.producer.publish(KafkaTopics.TIPSC, ...)
            return None
        return self.tipsc_reeval_worker.execute(
            preeval,
            validation_context,
            compliance_context,
            followup_context,
        )
    
