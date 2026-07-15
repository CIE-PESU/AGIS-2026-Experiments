from enum import Enum


class KafkaTopics(str, Enum):

    PRE_EVAL = "userSession.preeval"

    VALIDATION = "userSession.validation"

    REGULATORY = "userSession.regulatory"

    ETHICS = "userSession.ethics"

    TIPSC = "userSession.tipsc"

    FOLLOWUP = "userSession.followup"

    DFV = "userSession.dfv"

    NOTIFICATIONS = "userSession.notifications"

    VALIDATION_DLQ = "userSession.validation.dlq"

    ETHICS_DLQ = "userSession.ethics.dlq"

    TIPSC_DLQ = "userSession.tipsc.dlq"