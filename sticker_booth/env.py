"""Tiny .env loader (no extra dependency) plus a UTF-8 console fix for Windows."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env(path=None):
    """Read KEY=VALUE lines from .env into os.environ. Existing env vars win. Values are never printed."""
    candidates = [Path(path)] if path else [Path.cwd() / ".env", REPO_ROOT / ".env"]
    for p in candidates:
        if p.is_file():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().removeprefix("export ").strip()
                v = v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
            return p
    return None


def utf8_console():
    """Windows consoles default to cp1252 and crash on emoji; switch stdout/stderr to UTF-8."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
