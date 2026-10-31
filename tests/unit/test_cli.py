import json

import pytest

from hisinone import cli
from hisinone.errors import UsageError


def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    for name in ("HISINONE_BASE_URL", "HISINONE_USER", "HISINONE_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def _json_stdout(capsys):
    return json.loads(capsys.readouterr().out)


def test_fehlendes_argument_ist_json_usage_fehler(monkeypatch, tmp_path, capsys):
    _clean_env(monkeypatch, tmp_path)
    assert cli.main(["suche"]) == 2
    data = _json_stdout(capsys)
    assert data["fehler"]["code"] == 2
    assert data["fehler"]["naechster_schritt"] == "hisinone --help"


def test_stundenplan_ohne_sitzung_meldet_login(monkeypatch, tmp_path, capsys):
    _clean_env(monkeypatch, tmp_path)
    assert cli.main(["stundenplan", "--woche"]) == 4
    data = _json_stdout(capsys)
    assert data["fehler"]["naechster_schritt"] == "hisinone login"


def test_noten_ohne_sitzung_meldet_login(monkeypatch, tmp_path, capsys):
    _clean_env(monkeypatch, tmp_path)
    assert cli.main(["noten"]) == 4
    assert _json_stdout(capsys)["fehler"]["code"] == 4


def test_whoami_ohne_sitzung(monkeypatch, tmp_path, capsys):
    _clean_env(monkeypatch, tmp_path)
    assert cli.main(["whoami"]) == 4
    assert "hisinone login" in _json_stdout(capsys)["fehler"]["naechster_schritt"]


def test_login_ohne_portal_und_ohne_tty(monkeypatch, tmp_path, capsys):
    _clean_env(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert cli.main(["login"]) == 2
    assert "PORTAL" in _json_stdout(capsys)["fehler"]["naechster_schritt"]


def test_help_und_version_mit_exit_null(monkeypatch, tmp_path, capsys):
    _clean_env(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as hilfe:
        cli.main(["--help"])
    assert hilfe.value.code == 0
    with pytest.raises(SystemExit) as version:
        cli.main(["--version"])
    assert version.value.code == 0
    with pytest.raises(SystemExit) as sub:
        cli.main(["suche", "--help"])
    assert sub.value.code == 0


def test_ungueltiges_datum_wird_sauber_abgelehnt(monkeypatch):
    monkeypatch.setenv("HISINONE_HEUTE", "31.10.2026")
    with pytest.raises(UsageError) as fehler:
        cli._heute()
    assert "JJJJ-MM-TT" in fehler.value.naechster_schritt


def test_wochenberechnung():
    import datetime as dt

    kw, start, ende = cli._woche(dt.date(2026, 10, 31))
    assert kw == 44
    assert start == dt.date(2026, 10, 26)
    assert ende == dt.date(2026, 11, 1)
