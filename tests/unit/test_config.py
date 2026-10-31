import json
import stat

import pytest

from hisinone import config
from hisinone.errors import HisinoneError


def test_session_wird_mit_0600_gespeichert(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    data = {"portal": "http://127.0.0.1:1", "benutzer": "a@example.invalid"}
    path = config.save_session(data)
    assert path == tmp_path / "config" / "hisinone-cli" / "session.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert config.load_session() == data
    assert config.clear_session() is True
    assert config.clear_session() is False


def test_defekte_sitzungsdatei_meldet_naechsten_schritt(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    path = config.session_path()
    path.parent.mkdir(parents=True)
    path.write_text("{kaputt", encoding="utf-8")
    with pytest.raises(HisinoneError) as fehler:
        config.load_session()
    assert "defekt" in fehler.value.meldung
    assert fehler.value.naechster_schritt
    assert fehler.value.code == 1


def test_unvollstaendige_sitzungsdatei(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    path = config.session_path()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"benutzer": "x"}), encoding="utf-8")
    with pytest.raises(HisinoneError):
        config.load_session()
