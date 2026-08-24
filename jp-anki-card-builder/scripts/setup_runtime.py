#!/usr/bin/env python3
"""Create or check an isolated Python runtime for the pinned audio dependency."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path


REQUIRED_EDGE_TTS = "7.2.8"
SCRIPT_DIR = Path(__file__).resolve().parent


def runtime_python(runtime_dir: Path) -> Path:
    if os.name == "nt":
        return runtime_dir / "Scripts" / "python.exe"
    return runtime_dir / "bin" / "python"


def check_runtime(python_path: Path) -> tuple[bool, str]:
    if not python_path.is_file():
        return False, "runtime Python is missing"
    probe = subprocess.run(
        [
            str(python_path),
            "-c",
            "import importlib.metadata; print(importlib.metadata.version('edge-tts'))",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if probe.returncode != 0:
        return False, probe.stderr.strip() or "edge-tts is not installed"
    installed = probe.stdout.strip()
    if installed != REQUIRED_EDGE_TTS:
        return False, f"edge-tts {installed} is installed; expected {REQUIRED_EDGE_TTS}"
    return True, installed


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_dir", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    runtime_dir = args.runtime_dir.resolve()
    python_path = runtime_python(runtime_dir)

    valid, detail = check_runtime(python_path)
    if valid:
        print(json.dumps({"status": "ok", "python": str(python_path), "edge_tts": detail}))
        return 0
    if args.check_only:
        print(json.dumps({"status": "missing", "python": str(python_path), "detail": detail}))
        return 2
    if runtime_dir.exists():
        print(
            json.dumps(
                {
                    "status": "error",
                    "errors": [
                        "runtime directory exists but is not valid; choose a new empty directory instead of deleting it automatically",
                        detail,
                    ],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    try:
        venv.EnvBuilder(with_pip=True, clear=False).create(runtime_dir)
        python_path = runtime_python(runtime_dir)
        environment = os.environ.copy()
        environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        environment["PYTHONUTF8"] = "1"
        subprocess.run(
            [
                str(python_path),
                "-m",
                "pip",
                "install",
                "--no-input",
                "-r",
                str(SCRIPT_DIR / "requirements.txt"),
            ],
            check=True,
            env=environment,
        )
        valid, detail = check_runtime(python_path)
        if not valid:
            raise RuntimeError(detail)
        print(json.dumps({"status": "ok", "python": str(python_path), "edge_tts": detail}))
        return 0
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
