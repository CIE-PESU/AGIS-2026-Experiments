"""
kafka/topics.py — Kafka topic name constants.

Single source of truth for all Kafka topic strings used by the backend.
Workers subscribe to these same topics.

Naming convention: <domain>.<consumer>
"""


class KafkaTopic:
    """All Kafka topic names used across AGIS workers."""

    # Published by the backend when a session is created.
    # Consumed by the TIPSC worker to run the T-I-P-S-C evaluation.
    USER_SESSION_TIPSC = "userSession.tipsc"

    # Published by the backend when TIPSC completes with ready_for_dfv=True.
    # Consumed by the DFV worker.
    USER_SESSION_DFV = "userSession.dfv"

    # Published by the backend when DFV completes.
    # Consumed by the Discovery worker.
    USER_SESSION_DISCOVERY = "userSession.discovery"
