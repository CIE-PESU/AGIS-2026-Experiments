"""Separate saved, completed reports from queued or failed flow records."""


def completed_flow_output(flow) -> dict | None:
    if hasattr(flow, "model_dump"):
        flow = flow.model_dump()
    if not isinstance(flow, dict) or flow.get("status") not in {"done", "completed"}:
        return None
    output = flow.get("output")
    return output if isinstance(output, dict) and output else None
