#!/usr/bin/env python3
"""Create or verify an isolated runtime shared by all skill installations."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


IMPORTS = ("numpy", "pandas", "vectorbt", "reportlab", "pypdf", "matplotlib", "pyarrow", "flask")


def _python(venv: Path) -> Path:
    unix = venv / "bin" / "python"
    windows = venv / "Scripts" / "python.exe"
    return unix if unix.exists() else windows


def _check(python: Path) -> bool:
    if not python.is_file():
        return False
    code = "; ".join(f"import {name}" for name in IMPORTS)
    return subprocess.run([str(python), "-c", code], check=False, capture_output=True).returncode == 0


def _supported(python: Path) -> bool:
    if not python.is_file():
        return False
    code = "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 15) else 1)"
    return subprocess.run([str(python), "-c", code], check=False, capture_output=True).returncode == 0


def _local_python() -> str:
    candidates = ("python3.14", "python3.13", "python3.12", "python3.11")
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable and _supported(Path(executable)):
            return executable
    if _supported(Path(sys.executable)):
        return sys.executable
    raise SystemExit("Python 3.11 through 3.14 is required; install it or install uv")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    skill = Path(__file__).resolve().parents[1]
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    venv = Path(os.environ.get("EVOLVE_STRATEGY_RUNTIME", cache_root / "evolve-trading-strategy" / "runtime"))
    requirements = skill / "requirements.txt"
    python = _python(venv)
    if args.check:
        accepted = _check(python)
        print(json.dumps({"accepted": accepted, "runtime": str(python) if python.exists() else None}))
        return 0 if accepted else 1
    uv = shutil.which("uv")
    if python.exists() and not _supported(python):
        shutil.rmtree(venv)
        python = _python(venv)
    if uv:
        if not python.exists():
            subprocess.run([uv, "venv", str(venv), "--python", ">=3.11,<3.15"], check=True)
        subprocess.run([uv, "pip", "install", "--python", str(_python(venv)), "-r", str(requirements)], check=True)
    else:
        if not python.exists():
            subprocess.run([_local_python(), "-m", "venv", str(venv)], check=True)
        subprocess.run([str(_python(venv)), "-m", "pip", "install", "-r", str(requirements)], check=True)
    if not _check(_python(venv)):
        raise SystemExit("runtime dependency check failed")
    print(json.dumps({"accepted": True, "runtime": str(_python(venv))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
