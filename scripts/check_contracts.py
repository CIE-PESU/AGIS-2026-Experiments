"""Check OpenAPI, database schema, and backend/frontend state contract in CI."""
from pathlib import Path
import json
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "tests/conftest.py"))
sys.path.insert(0, str(ROOT / "backend"))
from scripts.export_openapi import main  # noqa: E402
sys.argv = ["export_openapi", "--check"]
main()
from scripts.validate_openapi import validate  # noqa: E402
errors = validate(str(ROOT / "docs/api-spec-generated.json"))
if errors:
    raise SystemExit("\n".join(errors))
from state_machine.states import SessionStatus  # noqa: E402
source = (ROOT / "frontend/src/types/api.ts").read_text()
for state in SessionStatus:
    if f'"{state.value}"' not in source:
        raise SystemExit(f"Frontend session status missing: {state.value}")
print("Mounted routes and frontend statuses match backend contracts")

from models.session import Session
if json.loads((ROOT / "docs/schema.json").read_text()) != Session.model_json_schema(mode="serialization"):
    raise SystemExit("Persisted session schema is stale")
