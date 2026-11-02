"""Check tracked source syntax, structured data, and local documentation links."""

import ast
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]


def unique_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def main() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    failures = []
    checked = 0
    for filename in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        path = ROOT / filename
        if not path.is_file() or path.suffix not in {
            ".py",
            ".json",
            ".ipynb",
            ".toml",
            ".yml",
            ".yaml",
            ".md",
        }:
            continue
        try:
            source = path.read_text(encoding="utf-8")
            if path.suffix == ".py":
                ast.parse(source, filename=filename)
            elif path.suffix in {".json", ".ipynb"}:
                json.loads(source, object_pairs_hook=unique_json_keys)
            elif path.suffix == ".toml":
                tomllib.loads(source)
            elif path.suffix in {".yml", ".yaml"}:
                yaml.safe_load(source)
            else:
                for target in re.findall(r"\]\(([^)]+)\)", source):
                    target = target.split(' "', 1)[0].strip("<>")
                    parsed = urlsplit(target)
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    local = (
                        ROOT / unquote(parsed.path).lstrip("/")
                        if parsed.path.startswith("/")
                        else path.parent / unquote(parsed.path)
                    )
                    if not local.exists():
                        raise ValueError(f"Missing documentation target: {target}")
            checked += 1
        except (ValueError, SyntaxError, UnicodeError, OSError, yaml.YAMLError) as exc:
            failures.append(f"{filename}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Repository syntax/data/documentation checks passed for {checked} files")


if __name__ == "__main__":
    main()
