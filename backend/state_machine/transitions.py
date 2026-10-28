"""
state_machine/transitions.py

Defines every legal AGIS session lifecycle transition.

This is the backend state transition contract.
"""

from state_machine.states import SessionStatus


ALLOWED_TRANSITIONS: dict[
    SessionStatus,
    frozenset[SessionStatus],
] = {

    # ──────────────────────────────────────────────────────────────────────
    # Session creation
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.CREATED: frozenset({
        SessionStatus.QUEUED,
        SessionStatus.FAILED,
        SessionStatus.ARCHIVED,
    }),

    SessionStatus.QUEUED: frozenset({
        SessionStatus.PRE_EVAL,
        SessionStatus.TIPSC_RUNNING,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
    }),

    # ──────────────────────────────────────────────────────────────────────
    # TIPSC pipeline
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.PRE_EVAL: frozenset({
        SessionStatus.VALIDATION_RUNNING,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.VALIDATION_RUNNING: frozenset({
        SessionStatus.ETHICS_RUNNING,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.ETHICS_RUNNING: frozenset({
        SessionStatus.TIPSC_RUNNING,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.TIPSC_RUNNING: frozenset({
        SessionStatus.WAITING_FOR_FOUNDER,
        SessionStatus.TIPSC_COMPLETED,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
    }),

    # ──────────────────────────────────────────────────────────────────────
    # Founder follow-up loop
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.WAITING_FOR_FOUNDER: frozenset({
        SessionStatus.TIPSC_REEVALUATION,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
        SessionStatus.ARCHIVED,
    }),

    SessionStatus.TIPSC_REEVALUATION: frozenset({
        SessionStatus.WAITING_FOR_FOUNDER,
        SessionStatus.TIPSC_COMPLETED,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.FAILED,
    }),

    # ──────────────────────────────────────────────────────────────────────
    # TIPSC completed
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.TIPSC_COMPLETED: frozenset({
        SessionStatus.DFV_WAITING,
        SessionStatus.ARCHIVED,
    }),

    SessionStatus.TIPSC_FAILED: frozenset({
        SessionStatus.QUEUED,
        SessionStatus.ARCHIVED,
    }),

    # ──────────────────────────────────────────────────────────────────────
    # DFV
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.DFV_WAITING: frozenset({
        SessionStatus.DFV_WAITING,
        SessionStatus.DFV_RUNNING,
        SessionStatus.DFV_COMPLETED,
        SessionStatus.DFV_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.DFV_RUNNING: frozenset({
        SessionStatus.DFV_COMPLETED,
        SessionStatus.DFV_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.DFV_COMPLETED: frozenset({
        SessionStatus.DFV_WAITING,
        SessionStatus.DISCOVERY_WAITING,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),

    SessionStatus.DFV_FAILED: frozenset({
    SessionStatus.DFV_WAITING,
    SessionStatus.ARCHIVED,
    }),
    # ──────────────────────────────────────────────────────────────────────
    # Discovery
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.DISCOVERY_WAITING: frozenset({
        SessionStatus.DISCOVERY_RUNNING,
        SessionStatus.PMF_WAITING,
        SessionStatus.COMPLETED, 
        SessionStatus.DISCOVERY_FAILED,
        SessionStatus.FAILED,
        SessionStatus.DFV_WAITING,
    }),

    SessionStatus.DISCOVERY_RUNNING: frozenset({
        SessionStatus.PMF_WAITING,
        SessionStatus.COMPLETED,
        SessionStatus.DISCOVERY_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.DISCOVERY_FAILED: frozenset({
        SessionStatus.DISCOVERY_WAITING,
        SessionStatus.ARCHIVED,
        SessionStatus.DFV_WAITING,
    }),
    # ──────────────────────────────────────────────────────────────────────
    # PMF
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.PMF_WAITING: frozenset({
        SessionStatus.PMF_WAITING,
        SessionStatus.PMF_RUNNING,
        SessionStatus.PMF_COMPLETED,
        SessionStatus.PMF_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.PMF_RUNNING: frozenset({
        SessionStatus.PMF_COMPLETED,
        SessionStatus.PMF_FAILED,
        SessionStatus.FAILED,
    }),

    SessionStatus.PMF_COMPLETED: frozenset({
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),

    SessionStatus.PMF_FAILED: frozenset({
        SessionStatus.PMF_WAITING,
        SessionStatus.ARCHIVED,
    }),
    # ──────────────────────────────────────────────────────────────────────
    # Global terminal states
    # ──────────────────────────────────────────────────────────────────────

    SessionStatus.COMPLETED: frozenset({
        SessionStatus.DFV_WAITING,
        SessionStatus.PMF_WAITING,
    }),

    SessionStatus.FAILED: frozenset({
        SessionStatus.ARCHIVED,
    }),

    SessionStatus.ARCHIVED: frozenset(),
}