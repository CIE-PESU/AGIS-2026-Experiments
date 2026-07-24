import logging

from engine.kafka.message import WorkerMessage

logger = logging.getLogger(__name__)


class MessageProducer:

    def publish(
        self,
        topic,
        message: WorkerMessage,
    ):

        logger.info(
            f"[MOCK PRODUCER] Publishing to {topic}"
        )

        logger.info(
            f"Correlation ID: {message.correlation_id}"
        )

        logger.debug(message)