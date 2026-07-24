from .base import KafkaException


class KafkaPublishError(KafkaException):
    """Raised when publishing a message to Kafka fails."""

    def __init__(self):
        super().__init__(
            message="Failed to publish message to Kafka.",
            status_code=503,
            error_code="KAFKA_PUBLISH_ERROR",
        )


class KafkaUnavailableError(KafkaException):
    """Raised when the Kafka service is unavailable."""

    def __init__(self):
        super().__init__(
            message="Kafka service is unavailable.",
            status_code=503,
            error_code="KAFKA_UNAVAILABLE",
        )