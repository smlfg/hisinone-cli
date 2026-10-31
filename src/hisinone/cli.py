"""Kommandozeile für hisinone."""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import sys

from . import __version__
from .client import (
    DEFAULT_BASE_URL,
    HisinoneClient,
    client_for_portal,
    normalize_base_url,
    resolve_portal,
)
from .config import clear_session, load_session, save_session
from .errors import HisinoneError, LoginRequired, UsageError
from .parse import Treffer, Veranstaltung

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message, "hisinone --help")


def _add_json_option(parser: argparse.ArgumentParser, *, suppress: bool = False) -> None:
    kwargs: dict[str, object] = {
        "action": "store_true",
        "help": "JSON auf stdout ausgeben (automatisch, wenn stdout kein Terminal ist)",
    }
    if suppress:
        kwargs["default"] = argparse.SUPPRESS
    parser.add_argument("--json", **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="hisinone",
        description="HISinOne-Campusportale im Terminal.",
    )
    parser.add_argument(
        "--version", action="version", version=f"hisinone {__version__}"
    )
    _add_json_option(parser)
    subparsers = parser.add_subparsers(dest="command", metavar="BEFEHL")

    login = subparsers.add_parser(
        "login", help="anmelden und Sitzung lokal speichern"
    )
    login.add_argument(
        "portal", nargs="?", metavar="PORTAL", help="Portal-Adresse oder Hochschulname"
    )
    _add_json_option(login, suppress=True)
    login.set_defaults(handler=_cmd_login)

    logout = subparsers.add_parser("logout", help="lokale Sitzung löschen")
    _add_json_option(logout, suppress=True)
    logout.set_defaults(handler=_cmd_logout)

    whoami = subparsers.add_parser("whoami", help="gespeicherte Sitzung anzeigen")
    _add_json_option(whoami, suppress=True)
    whoami.set_defaults(handler=_cmd_whoami)

    suche = subparsers.add_parser("suche", help="öffentliche Veranstaltungssuche")
    suche.add_argument("begriff", metavar="BEGRIFF", help="Titel, Nummer oder Lehrperson")
    _add_json_option(suche, suppress=True)
    suche.set_defaults(handler=_cmd_suche)

    veranstaltung = subparsers.add_parser(
        "veranstaltung", help="Veranstaltungsdetails anzeigen"
    )
    veranstaltung.add_argument(
        "name", metavar="NAME", help="Veranstaltungstitel (ganz oder eindeutig)"
    )
    _add_json_option(veranstaltung, suppress=True)
    veranstaltung.set_defaults(handler=_cmd_veranstaltung)

    stundenplan = subparsers.add_parser(
        "stundenplan", help="persönlichen Stundenplan anzeigen"
    )
    stundenplan.add_argument(
        "--woche", action="store_true", help="ganze Kalenderwoche statt heute"
    )
    _add_json_option(stundenplan, suppress=True)
    stundenplan.set_defaults(handler=_cmd_stundenplan)

    noten = subparsers.add_parser("noten", help="Leistungsübersicht anzeigen")
    _add_json_option(noten, suppress=True)
    noten.set_defaults(handler=_cmd_noten)

    return parser


def _json_mode(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False)) or not sys.stdout.isatty()


def _emit_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _emit_text(text: str) -> None:
    print(text)


def _read_prompt(prompt: str) -> str:
    sys.stderr.write(prompt)
    sys.stderr.flush()
    line = sys.stdin.readline()
    if not line:
        raise UsageError(
            "Eingabe abgebrochen.", "hisinone login erneut starten"
        )
    return line.rstrip("\r\n")


def _read_password() -> str:
    try:
        return getpass.getpass("Passwort: ", stream=sys.stderr)
    except EOFError as exc:
        raise UsageError(
            "Eingabe abgebrochen.", "hisinone login erneut starten"
        ) from exc


def _choose_portal(argument: str | None) -> str:
    portal = resolve_portal(argument)
    if portal:
        return portal
    if not sys.stdin.isatty():
        raise UsageError(
            "Portal-Adresse fehlt.",
            "hisinone login PORTAL oder HISINONE_BASE_URL setzen",
        )
    answer = _read_prompt("Portal-Adresse oder Hochschulname: ")
    if not answer.strip():
        raise UsageError(
            "Portal-Adresse fehlt.", "hisinone login PORTAL oder HISINONE_BASE_URL setzen"
        )
    return normalize_base_url(answer)


def _personal_portal(session: dict[str, object]) -> str:
    from_env = os.environ.get("HISINONE_BASE_URL")
    if from_env:
        return normalize_base_url(from_env)
    return str(session.get("portal") or DEFAULT_BASE_URL)


def _cmd_login(args: argparse.Namespace) -> int:
    portal = _choose_portal(args.portal)
    benutzer = os.environ.get("HISINONE_USER", "")
    if not benutzer:
        if not sys.stdin.isatty():
            raise UsageError(
                "Benutzername fehlt.", "HISINONE_USER setzen oder hisinone login im Terminal"
            )
        benutzer = _read_prompt("Benutzer: ")
        if not benutzer.strip():
            raise UsageError("Benutzername fehlt.", "hisinone login erneut starten")
    passwort = os.environ.get("HISINONE_PASSWORD", "")
    if not passwort:
        if not sys.stdin.isatty():
            raise UsageError(
                "Passwort fehlt.",
                "HISINONE_PASSWORD setzen oder hisinone login im Terminal",
            )
        passwort = _read_password()
    client = HisinoneClient(portal)
    session = client.login(benutzer.strip(), passwort)
    save_session(session)
    if _json_mode(args):
        _emit_json(
            {
                "angemeldet": True,
                "portal": session.get("portal"),
                "benutzer": session.get("benutzer"),
            }
        )
    else:
        _emit_text("Login erfolgreich")
    return 0


def _cmd_logout(args: argparse.Namespace) -> int:
    removed = clear_session()
    if _json_mode(args):
        _emit_json({"angemeldet": False})
    else:
        _emit_text("Abgemeldet." if removed else "Nicht angemeldet.")
    return 0


def _cmd_whoami(args: argparse.Namespace) -> int:
    session = load_session()
    if session is None:
        raise LoginRequired("Nicht angemeldet.", "hisinone login")
    if _json_mode(args):
        _emit_json(
            {
                "angemeldet": True,
                "portal": session.get("portal"),
                "benutzer": session.get("benutzer"),
            }
        )
    else:
        _emit_text(f"Portal: {session.get('portal')}")
        _emit_text(f"Benutzer: {session.get('benutzer')}")
    return 0


def _public_client(args: argparse.Namespace) -> HisinoneClient:
    return HisinoneClient(resolve_portal() or DEFAULT_BASE_URL)


def _cmd_suche(args: argparse.Namespace) -> int:
    treffer = _public_client(args).search(args.begriff)
    if _json_mode(args):
        _emit_json(
            {
                "suche": args.begriff,
                "treffer": [item.to_dict() for item in treffer],
            }
        )
        return 0
    if not treffer:
        _emit_text("Keine Treffer.")
        return 0
    for item in treffer:
        suffix = f" – {item.art}" if item.art else ""
        _emit_text(
            f"{item.nummer}) {item.titel} (Veranstaltung {item.unit_id}){suffix}"
        )
    return 0


def _list_treffer(treffer: list[Treffer]) -> None:
    for item in treffer:
        suffix = f" – {item.art}" if item.art else ""
        _emit_text(
            f"{item.nummer}) {item.titel} (Veranstaltung {item.unit_id}){suffix}"
        )


def _pick_treffer(treffer: list[Treffer], name: str, json_mode: bool) -> Treffer | None:
    exact = [item for item in treffer if item.titel.casefold() == name.casefold()]
    if len(exact) == 1:
        return exact[0]
    if len(treffer) == 1:
        return treffer[0]
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        if json_mode:
            _emit_json(
                {
                    "treffer": [item.to_dict() for item in treffer],
                    "fehler": {
                        "code": 2,
                        "meldung": "Mehrere Treffer, Auswahl ohne Terminal nicht möglich.",
                        "naechster_schritt": "Namen genauer angeben, z. B. hisinone veranstaltung \"Titel\"",
                    },
                }
            )
        else:
            _list_treffer(treffer)
            sys.stderr.write(
                "Mehrere Treffer. Nächster Schritt: Namen genauer angeben, "
                "z. B. hisinone veranstaltung \"Titel\"\n"
            )
        return None
    _list_treffer(treffer)
    while True:
        answer = _read_prompt(f"Auswahl (1-{len(treffer)}): ").strip()
        if not answer:
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(treffer):
            return treffer[int(answer) - 1]
        sys.stderr.write(f"Bitte eine Zahl von 1 bis {len(treffer)} eingeben.\n")
        sys.stderr.flush()


def _format_termin(termin) -> str:
    zeit = f"{termin.von}-{termin.bis}" if termin.von and termin.bis else ""
    zeitraum = f"{termin.start}-{termin.ende}" if termin.start and termin.ende else ""
    parts = [termin.wochentag, zeit]
    line = " ".join(part for part in parts if part)
    if zeitraum:
        line = f"{line}, {zeitraum}" if line else zeitraum
    return f"Termin: {line}"


def _emit_veranstaltung(veranstaltung: Veranstaltung) -> None:
    _emit_text(f"Titel: {veranstaltung.titel}")
    _emit_text(f"Art: {veranstaltung.art}")
    _emit_text(f"Semester: {veranstaltung.semester}")
    _emit_text(f"Lehrperson: {veranstaltung.lehrperson}")
    if not veranstaltung.termine:
        _emit_text("Termin: keine Angabe")
        return
    for termin in veranstaltung.termine:
        _emit_text(_format_termin(termin))
        _emit_text(f"Raum: {termin.raum}")


def _cmd_veranstaltung(args: argparse.Namespace) -> int:
    client = _public_client(args)
    treffer = client.search(args.name)
    if not treffer:
        raise HisinoneError(
            "Keine Veranstaltung gefunden.",
            "hisinone suche BEGRIFF ausprobieren",
        )
    chosen = _pick_treffer(treffer, args.name, _json_mode(args))
    if chosen is None:
        return 2
    if chosen.unit_id is None:
        raise HisinoneError(
            "Veranstaltungsnummer fehlt in der Trefferliste.",
            "hisinone suche BEGRIFF erneut ausführen",
        )
    veranstaltung = client.veranstaltung(chosen.unit_id, chosen.period_id)
    if not veranstaltung.titel:
        veranstaltung.titel = chosen.titel
    if not veranstaltung.art:
        veranstaltung.art = chosen.art
    if not veranstaltung.semester:
        veranstaltung.semester = chosen.semester
    if not veranstaltung.lehrperson:
        veranstaltung.lehrperson = chosen.lehrperson
    if veranstaltung.unit_id is None:
        veranstaltung.unit_id = chosen.unit_id
    if _json_mode(args):
        _emit_json(veranstaltung.to_dict())
    else:
        _emit_veranstaltung(veranstaltung)
    return 0


def _heute() -> dt.date:
    raw = os.environ.get("HISINONE_HEUTE")
    if not raw:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise UsageError(
            f"Ungültiges Datum in HISINONE_HEUTE: {raw!r}.",
            "Format JJJJ-MM-TT verwenden",
        ) from exc


def _woche(reference: dt.date) -> tuple[int, dt.date, dt.date]:
    start = reference - dt.timedelta(days=reference.weekday())
    return reference.isocalendar().week, start, start + dt.timedelta(days=6)


def _datum(value: dt.date) -> str:
    return value.strftime("%d.%m.%Y")


def _emit_stundenplan(
    plan, args: argparse.Namespace, reference: dt.date
) -> int:
    kw, start, ende = _woche(reference)
    if args.woche:
        header = f"Stundenplan KW {kw} ({_datum(start)} - {_datum(ende)})"
        termine = plan.termine
        json_data = {
            "woche": {"kw": kw, "start": _datum(start), "ende": _datum(ende)},
            "termine": termine,
        }
    else:
        tag = WOCHENTAGE[reference.weekday()]
        header = f"Stundenplan {tag} ({_datum(reference)})"
        termine = [
            item for item in plan.termine if item.get("wochentag") == tag
        ]
        json_data = {"tag": _datum(reference), "termine": termine}
    if _json_mode(args):
        _emit_json(json_data)
        return 0
    _emit_text(header)
    for item in termine:
        zeit = f"{item.get('von', '')}-{item.get('bis', '')}".strip("-")
        raum = item.get("raum", "")
        line = f"{item.get('wochentag', '')} {zeit} {item.get('titel', '')}".strip()
        if raum:
            line = f"{line} ({raum})"
        _emit_text(line)
    return 0


def _cmd_stundenplan(args: argparse.Namespace) -> int:
    session = load_session()
    if session is None:
        raise LoginRequired("Login fehlt.", "hisinone login")
    client = client_for_portal(_personal_portal(session), session)
    plan = client.stundenplan()
    return _emit_stundenplan(plan, args, _heute())


def _cmd_noten(args: argparse.Namespace) -> int:
    session = load_session()
    if session is None:
        raise LoginRequired("Login fehlt.", "hisinone login")
    client = client_for_portal(_personal_portal(session), session)
    leistungen = client.noten()
    if _json_mode(args):
        _emit_json({"leistungen": [item.to_dict() for item in leistungen]})
        return 0
    _emit_text("Leistungsübersicht")
    for item in leistungen:
        _emit_text(f"{item.modul}: {item.note} ({item.status})")
    return 0


def _report_error(error: HisinoneError, json_mode: bool) -> int:
    if json_mode:
        _emit_json(error.to_dict())
    else:
        sys.stderr.write(error.meldung + "\n")
        if error.naechster_schritt:
            sys.stderr.write(f"Nächster Schritt: {error.naechster_schritt}\n")
    return error.code


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    json_hint = "--json" in raw or not sys.stdout.isatty()
    parser = build_parser()
    try:
        args = parser.parse_args(raw)
    except UsageError as error:
        return _report_error(error, json_hint)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return int(args.handler(args))
    except HisinoneError as error:
        return _report_error(error, _json_mode(args))
    except (KeyboardInterrupt, EOFError):
        message = "Abgebrochen."
        if json_hint:
            _emit_json(
                {
                    "fehler": {
                        "code": 130,
                        "meldung": message,
                        "naechster_schritt": "hisinone --help",
                    }
                }
            )
        else:
            sys.stderr.write(f"{message} Nächster Schritt: hisinone --help\n")
        return 130
    except BrokenPipeError:
        return 1
    except Exception as error:  # noqa: BLE001 - nie Traceback auf der Konsole
        fallback = HisinoneError(
            f"Unerwarteter Fehler: {error}",
            "hisinone --help oder hisinone suche erneut versuchen",
        )
        return _report_error(fallback, _json_mode(args))


if __name__ == "__main__":
    raise SystemExit(main())
