"""
Flow trigger endpoints — POST /sessions/{id}/trigger/{tipsc,dfv,discovery}

Wiring note: this router imports `get_current_user` / `require_role` from
app.dependencies.auth (Palash, B-01/B-02) and constructs a FlowService with
real session_repo / kafka_producer / audit_service instances. Those three
real implementations (Bhavesh's B-04, Vijay's B-06, Palash's B-08) need to
be on develop-backend for this file to actually run — flow_service.py
itself has no such dependency and is unit-tested standalone
(tests/test_flow_service.py).

`get_flow_service` below is a placeholder wiring function — swap the
`...` for the real singletons once those branches land.
"""

from fastapi import APIRouter, Depends

from app.dependencies.auth import CurrentUser, get_current_user, require_role
from app.schemas.flow import DFVTriggerRequest, FlowTriggerResponse
from app.services.flow_service import FlowService

router = APIRouter(prefix="/sessions", tags=["Flows"])


def get_flow_service() -> FlowService:
    """
    TODO: replace with real singletons once B-04 (session_repo), B-06
    (kafka_producer), and B-08 (audit_service) are on develop-backend.
    """
    raise NotImplementedError(
        "Wire real session_repo / kafka_producer / audit_service here "
        "once B-04 / B-06 / B-08 are merged."
    )


@router.post("/{session_id}/trigger/tipsc", response_model=FlowTriggerResponse)
async def trigger_tipsc(
    session_id: str,
    current_user: CurrentUser = Depends(require_role(["student"])),
    flow_service: FlowService = Depends(get_flow_service),
):
    result = await flow_service.trigger_tipsc(session_id, current_user.user_id)
    return result


@router.post("/{session_id}/trigger/dfv", response_model=FlowTriggerResponse)
async def trigger_dfv(
    session_id: str,
    body: DFVTriggerRequest,
    current_user: CurrentUser = Depends(require_role(["student"])),
    flow_service: FlowService = Depends(get_flow_service),
):
    result = await flow_service.trigger_dfv(
        session_id, current_user.user_id, body.model_dump()
    )
    return result


@router.post("/{session_id}/trigger/discovery", response_model=FlowTriggerResponse)
async def trigger_discovery(
    session_id: str,
    current_user: CurrentUser = Depends(require_role(["student"])),
    flow_service: FlowService = Depends(get_flow_service),
):
    result = await flow_service.trigger_discovery(session_id, current_user.user_id)
    return result