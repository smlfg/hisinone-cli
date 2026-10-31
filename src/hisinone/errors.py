"""Fehlerklassen mit festen Exit-Codes."""

from __future__ import annotations


class HisinoneError(Exception):
    """Fehler mit Exit-Code, lesbarer Meldung und nächstem Schritt."""

    code = 1

    def __init__(self, meldung: str, naechster_schritt: str | None = None) -> None:
        super().__init__(meldung)
        self.meldung = meldung
        self.naechster_schritt = naechster_schritt

    def to_dict(self) -> dict[str, object]:
        return {
            "fehler": {
                "code": self.code,
                "meldung": self.meldung,
                "naechster_schritt": self.naechster_schritt,
            }
        }


class UsageError(HisinoneError):
    code = 2


class NetworkError(HisinoneError):
    code = 3


class LoginRequired(HisinoneError):
    code = 4


class LoginFailed(HisinoneError):
    code = 5
