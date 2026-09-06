"""Run the deterministic document-tools verification suite inside Docker."""

from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    ROOT / "backend" / "api.py",
    ROOT / "backend" / "artifacts.py",
    ROOT / "backend" / "dispatcher.py",
    ROOT / "backend" / "migrations.py",
    ROOT / "backend" / "tasks.py",
    ROOT / "backend" / "tool_contracts.py",
    ROOT / "backend" / "tool_result_contracts.py",
    ROOT / "backend" / "tool_runner.py",
    ROOT / "platform_client.py",
    ROOT / "platform_tools_ui.py",
    ROOT / "processor_optimized.py",
    ROOT / "web_search.py",
]


def main() -> int:
    if not all(compileall.compile_file(str(path), quiet=1) for path in MODULES):
        return 1
    if not compileall.compile_dir(str(ROOT / "backend" / "tooling"), quiet=1):
        return 1
    return subprocess.call([
        sys.executable, "-m", "pytest", "-q", "tests/unit", "tests/contracts",
        "--junitxml=/tmp/document-tools-unit.xml",
    ], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
