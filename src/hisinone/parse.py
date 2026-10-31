"""HTML-Auswertung für HISinOne-Seiten (nur Standardbibliothek)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

UNIT_ID_RE = re.compile(r"[?&](?:amp;)?unitId=(\d+)")
PERIOD_ID_RE = re.compile(r"[?&](?:amp;)?periodId=(\d+)")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Treffer:
    nummer: int
    titel: str
    art: str = ""
    unit_id: int | None = None
    semester: str = ""
    lehrperson: str = ""
    period_id: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "nummer": self.nummer,
            "titel": self.titel,
            "art": self.art,
            "unit_id": self.unit_id,
            "semester": self.semester,
            "lehrperson": self.lehrperson,
        }


@dataclass
class Termin:
    rhythmus: str = ""
    wochentag: str = ""
    von: str = ""
    bis: str = ""
    start: str = ""
    ende: str = ""
    raum: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "rhythmus": self.rhythmus,
            "wochentag": self.wochentag,
            "von": self.von,
            "bis": self.bis,
            "start": self.start,
            "ende": self.ende,
            "raum": self.raum,
        }


@dataclass
class Veranstaltung:
    titel: str = ""
    art: str = ""
    semester: str = ""
    lehrperson: str = ""
    unit_id: int | None = None
    termine: list[Termin] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "titel": self.titel,
            "art": self.art,
            "semester": self.semester,
            "lehrperson": self.lehrperson,
            "unit_id": self.unit_id,
            "termine": [termin.to_dict() for termin in self.termine],
        }


@dataclass
class Leistung:
    modul: str
    pruefung: str
    note: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "modul": self.modul,
            "pruefung": self.pruefung,
            "note": self.note,
            "status": self.status,
        }


@dataclass
class Stundenplan:
    ueberschrift: str = ""
    termine: list[dict[str, str]] = field(default_factory=list)


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1: list[str] = []
        self.tables: list[dict[str, object]] = []
        self._h1_depth = 0
        self._table: dict[str, object] | None = None
        self._nested_tables = 0
        self._row: list[dict[str, object]] | None = None
        self._cell: list[str] | None = None
        self._cell_tag = "td"
        self._cell_links: list[tuple[str, str]] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        if tag == "h1":
            self._h1_depth += 1
            return
        if tag == "table":
            if self._table is None:
                classes = set(values.get("class", "").split())
                self._table = {"classes": classes, "rows": []}
                self._nested_tables = 0
            else:
                self._nested_tables += 1
            return
        if self._table is None:
            return
        if tag == "tr":
            self._row = []
            return
        if tag in {"td", "th"} and self._row is not None:
            self._cell = []
            self._cell_tag = tag
            self._cell_links = []
            return
        if tag == "a" and self._cell is not None:
            self._link_href = values.get("href", "")
            self._link_text = []
            return

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            if self._h1_depth:
                self._h1_depth -= 1
            return
        if tag == "table":
            if self._table is None:
                return
            if self._nested_tables:
                self._nested_tables -= 1
            else:
                self.tables.append(self._table)
                self._table = None
            return
        if self._table is None:
            return
        if tag == "a" and self._link_href is not None:
            if self._cell is not None:
                self._cell_links.append(
                    (self._link_href, clean("".join(self._link_text)))
                )
            self._link_href = None
            self._link_text = []
            return
        if tag in {"td", "th"} and self._cell is not None:
            if self._row is not None:
                self._row.append(
                    {
                        "tag": self._cell_tag,
                        "text": clean("".join(self._cell)),
                        "links": list(self._cell_links),
                    }
                )
            self._cell = None
            self._cell_links = []
            return
        if tag == "tr" and self._row is not None:
            if self._table is not None and self._nested_tables == 0:
                rows = self._table["rows"]
                assert isinstance(rows, list)
                rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._h1_depth:
            self.h1.append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._link_href is not None:
            self._link_text.append(data)


def _parse_page(html: str) -> _PageParser:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return parser


def _table_rows(parser: _PageParser, css_class: str) -> list[list[dict[str, object]]]:
    for table in parser.tables:
        classes = table.get("classes")
        if isinstance(classes, set) and css_class in classes:
            rows = table.get("rows")
            if isinstance(rows, list):
                return rows
    return []


def _cell_text(row: list[dict[str, object]], index: int) -> str:
    if index >= len(row):
        return ""
    value = row[index].get("text")
    return str(value or "")


def _cell_links(row: list[dict[str, object]], index: int) -> list[tuple[str, str]]:
    if index >= len(row):
        return []
    links = row[index].get("links")
    if not isinstance(links, list):
        return []
    return [(str(href), str(text)) for href, text in links]


def parse_suche(html: str) -> list[Treffer]:
    parser = _parse_page(html)
    treffer: list[Treffer] = []
    for row in _table_rows(parser, "searchResults"):
        if not row or row[0].get("tag") == "th":
            continue
        links = _cell_links(row, 0)
        titel = links[0][1] if links else _cell_text(row, 0)
        if not titel:
            continue
        href = links[0][0] if links else ""
        unit_match = UNIT_ID_RE.search(href)
        period_match = PERIOD_ID_RE.search(href)
        treffer.append(
            Treffer(
                nummer=len(treffer) + 1,
                titel=titel,
                art=_cell_text(row, 1),
                unit_id=int(unit_match.group(1)) if unit_match else None,
                semester=_cell_text(row, 3),
                lehrperson=_cell_text(row, 2),
                period_id=int(period_match.group(1)) if period_match else None,
            )
        )
    return treffer


def _parse_zeitraum(text: str) -> tuple[str, str]:
    parts = re.split(r"\s*-\s*", text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


def parse_veranstaltung(html: str) -> Veranstaltung:
    parser = _parse_page(html)
    felder: dict[str, str] = {}
    for row in _table_rows(parser, "detail"):
        if len(row) >= 2:
            key = _cell_text(row, 0)
            if key:
                felder[key] = _cell_text(row, 1)

    unit_raw = felder.get("Veranstaltungsnummer", "")
    unit_match = re.search(r"\d+", unit_raw)
    veranstaltung = Veranstaltung(
        titel=felder.get("Titel", ""),
        art=felder.get("Veranstaltungsart", ""),
        semester=felder.get("Semester", ""),
        lehrperson=(
            felder.get("Verantwortliche/r")
            or felder.get("Durchführende/r")
            or felder.get("Verantwortliche")
            or ""
        ),
        unit_id=int(unit_match.group(0)) if unit_match else None,
    )

    for row in _table_rows(parser, "termine"):
        if not row or _cell_text(row, 0).lower() == "rhythmus":
            continue
        von, bis = _parse_zeitraum(_cell_text(row, 2))
        start, ende = _parse_zeitraum(_cell_text(row, 3))
        veranstaltung.termine.append(
            Termin(
                rhythmus=_cell_text(row, 0),
                wochentag=_cell_text(row, 1),
                von=von,
                bis=bis,
                start=start,
                ende=ende,
                raum=_cell_text(row, 4),
            )
        )
    return veranstaltung


def parse_stundenplan(html: str) -> Stundenplan:
    parser = _parse_page(html)
    plan = Stundenplan(ueberschrift=clean(" ".join(parser.h1)))
    for row in _table_rows(parser, "stundenplan"):
        if not row or _cell_text(row, 0).lower() == "tag":
            continue
        zeit = _cell_text(row, 1)
        von, bis = _parse_zeitraum(zeit)
        plan.termine.append(
            {
                "wochentag": _cell_text(row, 0),
                "von": von,
                "bis": bis,
                "titel": _cell_text(row, 2),
                "raum": _cell_text(row, 3),
            }
        )
    return plan


def parse_noten(html: str) -> list[Leistung]:
    parser = _parse_page(html)
    leistungen: list[Leistung] = []
    for row in _table_rows(parser, "noten"):
        if not row or _cell_text(row, 0).lower() == "modul":
            continue
        leistungen.append(
            Leistung(
                modul=_cell_text(row, 0),
                pruefung=_cell_text(row, 1),
                note=_cell_text(row, 2),
                status=_cell_text(row, 3),
            )
        )
    return leistungen


@dataclass
class Formular:
    action: str = ""
    method: str = "get"
    fields: list[tuple[str, str]] = field(default_factory=list)
    text_fields: list[str] = field(default_factory=list)
    password_fields: list[str] = field(default_factory=list)

    def payload(self, overrides: dict[str, str]) -> list[tuple[str, str]]:
        return [(name, overrides.get(name, value)) for name, value in self.fields]


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[Formular] = []
        self._form: Formular | None = None
        self._select: str | None = None
        self._select_options: list[tuple[str, str]] = []
        self._select_selected: str | None = None
        self._option_value: str | None = None
        self._option_selected = False
        self._option_text: list[str] = []
        self._textarea: str | None = None
        self._textarea_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        if tag == "form":
            self._form = Formular(
                action=values.get("action", ""),
                method=values.get("method", "get").lower(),
            )
            return
        if self._form is None:
            return
        if tag == "input":
            name = values.get("name", "")
            if not name:
                return
            kind = values.get("type", "text").lower()
            if kind in {"checkbox", "radio"} and "checked" not in values:
                return
            self._form.fields.append((name, values.get("value", "")))
            if kind == "password":
                self._form.password_fields.append(name)
            elif kind in {"text", "search", "email"}:
                self._form.text_fields.append(name)
            return
        if tag == "select":
            name = values.get("name", "")
            if not name:
                return
            self._select = name
            self._select_options = []
            self._select_selected = None
            return
        if tag == "option" and self._select is not None:
            self._option_value = values.get("value")
            self._option_selected = "selected" in values
            self._option_text = []
            return
        if tag == "textarea":
            name = values.get("name", "")
            if not name:
                return
            self._textarea = name
            self._textarea_text = []
            return

    def handle_endtag(self, tag: str) -> None:
        if self._form is None:
            return
        if tag == "form":
            self.forms.append(self._form)
            self._form = None
            return
        if tag == "option" and self._select is not None:
            text = clean("".join(self._option_text))
            value = self._option_value if self._option_value is not None else text
            self._select_options.append((value, text))
            if self._option_selected or (
                self._select_selected is None and len(self._select_options) == 1
            ):
                self._select_selected = value
            self._option_value = None
            self._option_text = []
            return
        if tag == "select" and self._select is not None:
            value = self._select_selected
            if value is None and self._select_options:
                value = self._select_options[0][0]
            self._form.fields.append((self._select, value or ""))
            self._select = None
            self._select_options = []
            self._select_selected = None
            return
        if tag == "textarea" and self._textarea is not None:
            self._form.fields.append(
                (self._textarea, clean("".join(self._textarea_text)))
            )
            self._textarea = None
            self._textarea_text = []

    def handle_data(self, data: str) -> None:
        if self._option_value is not None or (
            self._select is not None and self._option_text is not None
        ):
            if self._select is not None and self._option_text is not None:
                self._option_text.append(data)
        if self._textarea is not None:
            self._textarea_text.append(data)


def parse_formular(html: str) -> Formular | None:
    parser = _FormParser()
    parser.feed(html)
    parser.close()
    if not parser.forms:
        return None
    for form in parser.forms:
        if form.password_fields or form.text_fields:
            return form
    return parser.forms[0]


def parse_login_benutzer(html: str) -> str:
    match = re.search(r"Angemeldet als\s+([^<(]+)", html)
    return clean(match.group(1)) if match else ""


def ist_shibboleth(html: str) -> bool:
    text = html.lower()
    return any(
        marker in text
        for marker in (
            "shibboleth",
            "identity provider",
            "identityprovider",
            "single sign-on",
            "saml",
        )
    )
