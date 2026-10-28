"""Generate the API contract from the active app, or check that it is current."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from main import app  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/api-spec-generated.json")
    args = parser.parse_args()
    schema = app.openapi()
    from models.session import Session

    session_schema = (
        json.dumps(Session.model_json_schema(mode="serialization"), indent=2, sort_keys=True) + "\n"
    )
    schema_path = ROOT / "docs/schema.json"
    if args.check:
        if not schema_path.exists() or schema_path.read_text() != session_schema:
            raise SystemExit("Session schema is stale; regenerate OpenAPI")
    else:
        schema_path.write_text(session_schema)
    output = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != output:
            raise SystemExit(
                "OpenAPI is stale; run uv run python backend/scripts/export_openapi.py"
            )
    else:
        args.output.write_text(output)
    print("OpenAPI contract is current")


if __name__ == "__main__":
    main()
