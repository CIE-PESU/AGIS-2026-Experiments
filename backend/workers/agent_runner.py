"""Execute one agent in an isolated, terminable process (worker-private CLI)."""

import json
import sys
from pathlib import Path


def main():
    from workers.combined_agent_worker import (
        _load_dfv_agent,
        _load_discovery_agent,
        _parse_agent_output,
    )

    flow, result_path = sys.argv[1:]
    inputs = json.load(sys.stdin)
    if flow == "dfv":
        output = _parse_agent_output(_load_dfv_agent()(inputs))
    elif flow == "discovery":
        result = _load_discovery_agent()(inputs)
        output = {"report": getattr(result, "raw", str(result))}
    else:
        raise ValueError("Unknown agent")
    Path(result_path).write_text(json.dumps(output, default=str))


if __name__ == "__main__":
    main()
