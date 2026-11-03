"""Compatibility imports for Kafka errors defined in the shared error catalog."""

from .base import KafkaException, KafkaPublishError, KafkaUnavailableError

__all__ = ["KafkaException", "KafkaPublishError", "KafkaUnavailableError"]
