"""
Validates openapi.json fetched from the running FastAPI app in CI.

Checks:
  - File is valid JSON
  - Has top-level "openapi", "info", "paths" keys
  - "paths" is non-empty
  - Every path has at least one HTTP method with a "responses" block
  - The endpoints this team has actually built are present (spot check,
    not exhaustive — add to EXPECTED_PATH_PREFIXES as new routers land)

Usage: python -m scripts.validate_openapi <path-to-openapi.json>
"""

from __future__ import annotations

import json
import sys

EXPECTED_PATH_PREFIXES = [
    "/sessions",
    "/comments",
]

REQUIRED_TOP_LEVEL_KEYS = ["openapi", "info", "paths"]


def validate(schema_path: str) -> list[str]:
    errors: list[str] = []

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except json.JSONDecodeError as exc:
        return [f"openapi.json is not valid JSON: {exc}"]
    except FileNotFoundError:
        return [f"File not found: {schema_path}"]

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in schema:
            errors.append(f"Missing required top-level key: '{key}'")

    paths = schema.get("paths", {})
    if not paths:
        errors.append("'paths' is empty — no endpoints are registered")

    for path, methods in paths.items():
        if not isinstance(methods, dict) or not methods:
            errors.append(f"Path '{path}' has no HTTP methods defined")
            continue
        for method, operation in methods.items():
            if "responses" not in operation:
                errors.append(f"{method.upper()} {path} has no 'responses' block")

    found_prefixes = {
        prefix
        for prefix in EXPECTED_PATH_PREFIXES
        if any(p.startswith(prefix) for p in paths)
    }
    missing_prefixes = set(EXPECTED_PATH_PREFIXES) - found_prefixes
    for prefix in missing_prefixes:
        errors.append(
            f"Expected at least one path starting with '{prefix}' but found none "
            "(router not mounted in app.main, or not yet implemented)"
        )

    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.validate_openapi <path-to-openapi.json>")
        sys.exit(2)

    errors = validate(sys.argv[1])

    if errors:
        print("OpenAPI validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("OpenAPI validation passed.")


if __name__ == "__main__":
    main()