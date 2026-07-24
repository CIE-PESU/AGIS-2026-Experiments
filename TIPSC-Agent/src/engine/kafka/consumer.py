import logging

from engine.kafka.message import WorkerMessage

logger = logging.getLogger(__name__)


class MessageConsumer:

    def consume(
        self,
        topic,
    ) -> WorkerMessage:

        logger.info(
            f"[MOCK CONSUMER] Listening on {topic}"
        )

        return None