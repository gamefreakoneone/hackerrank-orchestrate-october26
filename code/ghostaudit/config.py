"""Environment configuration. Values are read from os.environ after an optional .env load; never logged."""
from __future__ import annotations

import os
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_DIR.parent
_dotenv_loaded = False


def _load_dotenv_once() -> None:
    """Load `code/.env` then `<repo>/.env` without overriding variables already set in the environment."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    for dotenv_path in (CODE_DIR / ".env", REPO_ROOT / ".env"):
        if not dotenv_path.is_file():
            continue
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip().removeprefix("export ").strip()
            value = value.strip().strip('"').strip("'")
            if name and value:
                os.environ.setdefault(name, value)


def env(name: str, default: str | None = None) -> str | None:
    _load_dotenv_once()
    value = os.environ.get(name, "").strip()
    return value or default


def require_env(name: str) -> str:
    value = env(name)
    if value is None:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value
