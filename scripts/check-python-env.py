"""Validate that AI Career Navigator is using the project Python venv."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_VENV = (PROJECT_ROOT / ".venv").resolve()
HERMES_MARKER = "hermes-agent"
REQUIRED_MODULES = ("uvicorn", "sqlalchemy", "email_validator", "eventlet")


def _norm(value: str | Path) -> str:
    return str(Path(value).resolve()).lower()


def _contains_hermes(value: str | Path) -> bool:
    return HERMES_MARKER in str(value).lower()


def _within_project_venv(value: str | Path) -> bool:
    try:
        Path(value).resolve().relative_to(PROJECT_VENV)
        return True
    except ValueError:
        return False


def fail(message: str) -> int:
    print("PROJECT_PYTHON_ENV_ERROR")
    print(f"reason={message}")
    print(f"expected_venv={PROJECT_VENV}")
    print(f"sys.executable={sys.executable}")
    print(f"sys.prefix={sys.prefix}")
    print("sys.path=")
    for path in sys.path:
        print(f"  {path}")
    return 1


def main() -> int:
    executable = Path(sys.executable).resolve()
    prefix = Path(sys.prefix).resolve()

    if not _within_project_venv(executable):
        return fail("sys.executable is not inside project .venv")

    if not _within_project_venv(prefix):
        return fail("sys.prefix is not inside project .venv")

    if _contains_hermes(executable) or _contains_hermes(prefix):
        return fail("interpreter points to Hermes venv")

    polluted_paths = [path for path in sys.path if _contains_hermes(path)]
    if polluted_paths:
        return fail("sys.path contains Hermes venv")

    for module_name in REQUIRED_MODULES:
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            return fail(f"missing required module: {module_name}")
        if _contains_hermes(spec.origin):
            return fail(f"{module_name} resolves to Hermes venv: {spec.origin}")
        if not _within_project_venv(spec.origin):
            return fail(f"{module_name} is not loaded from project .venv: {spec.origin}")

    print("PROJECT_PYTHON_ENV_OK")
    print(f"sys.executable={executable}")
    print(f"sys.prefix={prefix}")
    for module_name in REQUIRED_MODULES:
        spec = importlib.util.find_spec(module_name)
        print(f"{module_name}={spec.origin if spec else None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
