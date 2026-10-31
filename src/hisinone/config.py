"""Lokale Sitzungsdatei unter ~/.config/hisinone-cli/."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import HisinoneError

APP_DIR = "hisinone-cli"
SESSION_NAME = "session.json"


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / APP_DIR


def session_path() -> Path:
    return config_dir() / SESSION_NAME


def load_session() -> dict[str, object] | None:
    path = session_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise HisinoneError(
            f"Sitzungsdatei nicht lesbar: {exc}",
            "hisinone logout und erneut hisinone login",
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HisinoneError(
            "Sitzungsdatei ist defekt.",
            "hisinone logout ausführen und danach hisinone login",
        ) from exc
    if not isinstance(data, dict) or not data.get("portal"):
        raise HisinoneError(
            "Sitzungsdatei ist unvollständig.",
            "hisinone logout ausführen und danach hisinone login",
        )
    return data


def save_session(data: dict[str, object]) -> Path:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    path = session_path()
    fd, temporary = tempfile.mkstemp(prefix=".session-", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


def clear_session() -> bool:
    path = session_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise HisinoneError(
            f"Sitzungsdatei nicht löschbar: {exc}", "hisinone logout erneut versuchen"
        ) from exc
