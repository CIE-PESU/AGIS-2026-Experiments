"""Configuration and setup failures common to fresh desktop checkouts."""

import runpy
import sys
from pathlib import Path

from core.config import Settings
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]


def test_windows_bom_env_works_from_unrelated_directory(tmp_path, monkeypatch):
    checkout = tmp_path / "AGIS spaced café"
    checkout.mkdir()
    env = checkout / ".env"
    env.write_text("DEBUG=true\nAGIS_PORTABLE_TEST=café\n", encoding="utf-8-sig")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("AGIS_PORTABLE_TEST", raising=False)
    assert Settings(_env_file=env).DEBUG is True
    load_dotenv(env, encoding="utf-8-sig")
    import os

    assert os.environ["DEBUG"] == "true"
    assert os.environ["AGIS_PORTABLE_TEST"] == "café"


def test_setup_check_reports_partial_checkout_without_importing_core(tmp_path, monkeypatch, capsys):
    namespace = runpy.run_path(str(ROOT / "scripts/check_setup.py"))
    main = namespace["main"]
    main.__globals__["ROOT"] = tmp_path / "partial checkout café"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(namespace["shutil"], "which", lambda _: None)
    assert main() == 1
    output = capsys.readouterr().out
    assert "backend/core/processes.py" in output
    assert "complete repository checkout" in output
    assert "Missing root .env" in output
    assert "Node is missing" in output


def test_setup_check_rejects_unsupported_python(monkeypatch, capsys):
    namespace = runpy.run_path(str(ROOT / "scripts/check_setup.py"))
    monkeypatch.setattr(sys, "version_info", (3, 14, 0))
    assert namespace["main"]() == 1
    assert "Use Python 3.12 or 3.13" in capsys.readouterr().out
