"""
Unit tests for state_machine/ (B-05).

Covers every acceptance criterion from Day 1:
- All allowed transitions pass without exception
- All forbidden transitions raise InvalidStateTransitionError
- Archiving a RUNNING session raises an error
- Pure logic, no DB/model/kafka imports (checked by inspection, not a test)
"""

import itertools

import pytest

from app.state_machine.exceptions import InvalidStateTransitionError
from app.state_machine.states import RUNNING_STATES, SessionStatus
from app.state_machine.transitions import ALLOWED_TRANSITIONS
from app.state_machine.validator import validate_transition

ALLOWED_PAIRS = [
    (current, target)
    for current, targets in ALLOWED_TRANSITIONS.items()
    for target in targets
]

ALL_PAIRS = list(itertools.product(SessionStatus, SessionStatus))
FORBIDDEN_PAIRS = [pair for pair in ALL_PAIRS if pair not in ALLOWED_PAIRS]


@pytest.mark.parametrize("current,target", ALLOWED_PAIRS)
def test_allowed_transitions_pass(current, target):
    validate_transition(current, target)  # should not raise


@pytest.mark.parametrize("current,target", FORBIDDEN_PAIRS)
def test_forbidden_transitions_raise(current, target):
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(current, target)


@pytest.mark.parametrize("running_state", sorted(RUNNING_STATES, key=lambda s: s.value))
def test_cannot_archive_while_running(running_state):
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(running_state, SessionStatus.ARCHIVED)


def test_error_carries_current_and_target_state():
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_transition(SessionStatus.COMPLETED, SessionStatus.TIPSC_RUNNING)
    assert exc_info.value.current_status == SessionStatus.COMPLETED
    assert exc_info.value.target_status == SessionStatus.TIPSC_RUNNING


def test_specific_forbidden_transitions_from_arch_doc():
    """Spot-check the named forbidden cases from backend-arch.md Section 6.2."""
    forbidden_cases = [
        (SessionStatus.TIPSC_RUNNING, SessionStatus.DFV_RUNNING),
        (SessionStatus.TIPSC_COMPLETED, SessionStatus.TIPSC_RUNNING),
        (SessionStatus.COMPLETED, SessionStatus.DFV_RUNNING),
        (SessionStatus.ARCHIVED, SessionStatus.QUEUED),
        (SessionStatus.QUEUED, SessionStatus.COMPLETED),
        (SessionStatus.DFV_WAITING, SessionStatus.TIPSC_RUNNING),
    ]
    for current, target in forbidden_cases:
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(current, target)


def test_specific_allowed_transitions_from_arch_doc():
    happy_path = [
        (SessionStatus.CREATED, SessionStatus.QUEUED),
        (SessionStatus.QUEUED, SessionStatus.TIPSC_RUNNING),
        (SessionStatus.TIPSC_RUNNING, SessionStatus.TIPSC_COMPLETED),
        (SessionStatus.TIPSC_COMPLETED, SessionStatus.DFV_WAITING),
        (SessionStatus.DFV_WAITING, SessionStatus.DFV_RUNNING),
        (SessionStatus.DFV_RUNNING, SessionStatus.DFV_COMPLETED),
        (SessionStatus.DFV_COMPLETED, SessionStatus.DISCOVERY_WAITING),
        (SessionStatus.DISCOVERY_WAITING, SessionStatus.DISCOVERY_RUNNING),
        (SessionStatus.DISCOVERY_RUNNING, SessionStatus.COMPLETED),
        (SessionStatus.TIPSC_FAILED, SessionStatus.QUEUED),
    ]
    for current, target in happy_path:
        validate_transition(current, target)  # should not raise


def test_archive_allowed_from_non_running_non_archived_states():
    archivable = [
        SessionStatus.CREATED,
        SessionStatus.QUEUED,
        SessionStatus.TIPSC_COMPLETED,
        SessionStatus.TIPSC_FAILED,
        SessionStatus.DFV_WAITING,
        SessionStatus.DFV_COMPLETED,
        SessionStatus.DFV_FAILED,
        SessionStatus.DISCOVERY_WAITING,
        SessionStatus.DISCOVERY_FAILED,
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
    ]
    for state in archivable:
        validate_transition(state, SessionStatus.ARCHIVED)  # should not raise


def test_no_forbidden_module_imports():
    """
    Guard against accidental coupling: state_machine/ must not import
    models/, repositories/, or kafka/.
    """
    import ast
    import pathlib

    state_machine_dir = pathlib.Path(__file__).parent.parent / "app" / "state_machine"
    banned_prefixes = ("app.models", "app.repositories", "app.kafka")

    for py_file in state_machine_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(banned_prefixes), (
                    f"{py_file.name} imports from {node.module} — "
                    "state_machine must stay pure logic"
                )