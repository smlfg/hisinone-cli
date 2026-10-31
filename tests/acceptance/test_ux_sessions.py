"""Akzeptanztests aus den UX-Sitzungen (docs/UX.md).

Jeder Test startet das Tool als Subprozess in einem Pseudo-Terminal gegen den
Fake-Server aus tests/harness/. Das Tool erreicht nie einen echten Server.
Die Tests dürfen vor dem Bau (Schritt 4) rot sein.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "tests" / "harness"
sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer  # noqa: E402
from ux_session import PtySession, strip_ansi  # noqa: E402
from ux_spec import parse  # noqa: E402

LOGIN_USER = "max.mustermann@example.invalid"
LOGIN_PASSWORD = "geheim"


@pytest.fixture(scope="session")
def spec():
    parsed = parse(REPO / "docs" / "UX.md")
    assert not parsed.errors, parsed.errors
    return parsed


@pytest.fixture()
def server(spec):
    with FakeServer(spec, REPO) as fake:
        yield fake


def _tool_command() -> list[str]:
    override = os.environ.get("HISINONE_BIN")
    if override:
        return [override]
    found = shutil.which("hisinone")
    if found:
        return [found]
    return [sys.executable, "-m", "hisinone"]


def _env(server: FakeServer, home: Path) -> dict[str, str]:
    for relative in (".config", ".local/share", ".local/state", ".cache"):
        (home / relative).mkdir(parents=True, exist_ok=True)
    pythonpath = os.pathsep.join(
        part
        for part in (str(REPO / "src"), str(HARNESS), os.environ.get("PYTHONPATH", ""))
        if part
    )
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "HISINONE_BASE_URL": server.base_url,
            "HISINONE_HEUTE": "2026-10-31",
            "PYTHONPATH": pythonpath,
            "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1",
            "TERM": "xterm",
            "LANG": "C.UTF-8",
        }
    )
    env.pop("HISINONE_USER", None)
    env.pop("HISINONE_PASSWORD", None)
    return env


def _run_tty(
    args: list[str],
    env: dict[str, str],
    answers: list[tuple[str, str]] | None = None,
    timeout: float = 30.0,
) -> tuple[int | None, str]:
    session = PtySession(_tool_command() + args, env=env, cwd=str(REPO))
    try:
        for prompt, answer in answers or []:
            assert session.expect(prompt, timeout=timeout), (
                f"Prompt {prompt!r} nicht erschienen. Bisher:\n"
                + strip_ansi(session.transcript)
            )
            session.send_line(answer)
        code = session.wait_exit(timeout)
        return code, strip_ansi(session.transcript)
    finally:
        session.close()


def _login(server: FakeServer, home: Path) -> tuple[dict[str, str], str]:
    env = _env(server, home)
    code, output = _run_tty(
        ["login"],
        env,
        [(r"Benutzer", LOGIN_USER), (r"Passwort", LOGIN_PASSWORD)],
    )
    assert code == 0, output
    assert "Login erfolgreich" in output
    return env, output


def _session_file(home: Path) -> Path:
    return home / ".config" / "hisinone-cli" / "session.json"


def test_login_speichert_sitzung(server, tmp_path):
    home = tmp_path / "home"
    _, output = _login(server, home)
    assert LOGIN_USER in output or "Login erfolgreich" in output
    session = _session_file(home)
    assert session.is_file(), output
    assert stat.S_IMODE(session.stat().st_mode) == 0o600
    assert LOGIN_PASSWORD not in session.read_text(encoding="utf-8")


def test_suche_oberseminar(server, tmp_path):
    env = _env(server, tmp_path / "home")
    code, output = _run_tty(["suche", "Oberseminar"], env)
    assert code == 0, output
    assert "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung" in output
    assert "Oberseminar am Lehrstuhl Programmiersprachen" in output
    assert "Oberseminar am Lehrstuhl Rechnernetze und Telematik" in output
    assert "Veranstaltung 7586" in output


def test_veranstaltung_details(server, tmp_path):
    env = _env(server, tmp_path / "home")
    name = "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung"
    code, output = _run_tty(["veranstaltung", name], env)
    assert code == 0, output
    assert f"Titel: {name}" in output
    assert "Art: Seminar" in output
    assert "Semester: Wintersemester 2026/2027" in output
    assert "Lehrperson: Prof. Dr. A. Beispiel" in output
    assert "Termin: Di 16:00-18:00, 20.10.2026-09.02.2027" in output
    assert "Raum: SR 02 017 (G.-Köhler-Allee 052)" in output


def test_stundenplan_woche(server, tmp_path):
    home = tmp_path / "home"
    env, _ = _login(server, home)
    code, output = _run_tty(["stundenplan", "--woche"], env)
    assert code == 0, output
    assert "Stundenplan KW 44 (26.10.2026 - 01.11.2026)" in output
    assert "Mo 10:00-12:00 Algorithmen und Datenstrukturen (HS 101)" in output
    assert (
        "Di 16:00-18:00 Oberseminar am Lehrstuhl Mustererkennung und "
        "Bildverarbeitung (SR 02 017)" in output
    )


def test_noten(server, tmp_path):
    home = tmp_path / "home"
    env, _ = _login(server, home)
    code, output = _run_tty(["noten"], env)
    assert code == 0, output
    assert "Leistungsübersicht" in output
    assert "Algorithmen und Datenstrukturen: 1,7 (bestanden)" in output
    assert "Programmiersprachen: 2,3 (bestanden)" in output


def test_stundenplan_ohne_login_nennt_login(server, tmp_path):
    env = _env(server, tmp_path / "home")
    code, output = _run_tty(["stundenplan", "--woche"], env)
    assert code == 4, output
    assert "hisinone login" in output
    assert not _session_file(tmp_path / "home").exists()


def test_noten_ohne_login_nennt_login(server, tmp_path):
    env = _env(server, tmp_path / "home")
    code, output = _run_tty(["noten"], env)
    assert code == 4, output
    assert "hisinone login" in output


def test_suche_json(server, tmp_path):
    env = _env(server, tmp_path / "home")
    result = subprocess.run(
        _tool_command() + ["--json", "suche", "Oberseminar"],
        input="",
        env=env,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["suche"] == "Oberseminar"
    assert len(data["treffer"]) == 3
    assert data["treffer"][0]["unit_id"] == 7586
