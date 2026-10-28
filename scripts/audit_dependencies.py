"""Fail on new/changed advisories; print every explicitly documented upstream exception."""
import json
from pathlib import Path
import subprocess
import sys
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
exceptions = json.loads((ROOT / "docs/dependency-advisories.json").read_text())
result = subprocess.run([sys.executable, "-m", "pip_audit", "--format", "json", "--progress-spinner", "off"], capture_output=True, text=True)
try:
    report = json.loads(result.stdout)
except json.JSONDecodeError:
    raise SystemExit(result.stderr or "Dependency audit did not return a report")
failed = False
for dependency in report["dependencies"]:
    if dependency.get("skip_reason"):
        print(f"UNSCANNED DEPENDENCY: {dependency['name']}")
        failed = True
    for vulnerability in dependency.get("vulns", []):
        key = vulnerability["id"]
        known = exceptions.get(key)
        if known and known["package"] == dependency["name"] and known["version"] == dependency["version"] and date.today() < date.fromisoformat(known["review_by"]):
            print(f"KNOWN UPSTREAM RISK: {dependency['name']} {dependency['version']} {key}: {known['reason']}")
        else:
            print(f"UNREVIEWED ADVISORY: {dependency['name']} {dependency['version']} {key}")
            failed = True
if result.returncode not in (0, 1):
    raise SystemExit(result.stderr)
raise SystemExit(1 if failed else 0)
