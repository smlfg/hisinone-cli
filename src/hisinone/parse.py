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
        self._table_stack: list[dict[str, object]] = []
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
            if self._table is not None:
                self._table_stack.append(
                    {
                        "table": self._table,
                        "row": self._row,
                        "cell": self._cell,
                        "cell_tag": self._cell_tag,
                        "cell_links": self._cell_links,
                        "link_href": self._link_href,
                        "link_text": self._link_text,
                    }
                )
                self._row = None
                self._cell = None
                self._link_href = None
                self._link_text = []
            classes = set(values.get("class", "").split())
            self._table = {"classes": classes, "rows": []}
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
            self.tables.append(self._table)
            if self._table_stack:
                state = self._table_stack.pop()
                self._table = state["table"]  # type: ignore[assignment]
                self._row = state["row"]  # type: ignore[assignment]
                self._cell = state["cell"]  # type: ignore[assignment]
                self._cell_tag = str(state["cell_tag"])
                self._cell_links = state["cell_links"]  # type: ignore[assignment]
                self._link_href = state["link_href"]  # type: ignore[assignment]
                self._link_text = state["link_text"]  # type: ignore[assignment]
            else:
                self._table = None
                self._row = None
                self._cell = None
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
            if self._table is not None:
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


def _normalize_header(text: str) -> str:
    text = clean(text)
    text = re.sub(r"\s*\[[^\]]*\]\s*$", "", text)
    return text.casefold()


def _header_row(rows: list[list[dict[str, object]]]) -> tuple[int, list[str]]:
    for index, row in enumerate(rows):
        if row and all(cell.get("tag") == "th" for cell in row):
            return index, [_normalize_header(str(cell.get("text", ""))) for cell in row]
    return -1, []


def _column(headers: list[str], *needles: str) -> int | None:
    for index, header in enumerate(headers):
        if any(needle in header for needle in needles):
            return index
    return None


def _first_text(row: list[dict[str, object]], indices: list[int]) -> str:
    for index in indices:
        value = _cell_text(row, index).strip()
        if value:
            return value
    return ""


def _row_ids(row: list[dict[str, object]]) -> tuple[int | None, int | None]:
    unit_id: int | None = None
    period_id: int | None = None
    for cell in row:
        links = cell.get("links")
        if not isinstance(links, list):
            continue
        for href, _ in links:
            href = str(href)
            unit_match = UNIT_ID_RE.search(href)
            period_match = PERIOD_ID_RE.search(href)
            if unit_match and unit_id is None:
                unit_id = int(unit_match.group(1))
            if period_match and period_id is None:
                period_id = int(period_match.group(1))
    return unit_id, period_id


def parse_suche(html: str) -> list[Treffer]:
    parser = _parse_page(html)
    treffer: list[Treffer] = []
    title_priority = (
        "semesterabhängiger titel",
        "bezeichnung",
        "semesterunabhängiger titel",
        "titel",
    )
    for table in parser.tables:
        rows = table.get("rows")
        if not isinstance(rows, list):
            continue
        header_index, headers = _header_row(rows)
        if header_index < 0:
            continue
        title_indices = [
            headers.index(name) for name in title_priority if name in headers
        ]
        if not title_indices:
            continue
        art_index = _column(headers, "veranstaltungsart", "art")
        semester_index = (
            headers.index("semester") if "semester" in headers else _column(headers, "semester")
        )
        lehr_indices = [
            index
            for index, header in enumerate(headers)
            if "verantwortliche" in header or "durchführende" in header
        ]
        for row in rows[header_index + 1 :]:
            if not row or row[0].get("tag") == "th":
                continue
            titel = _first_text(row, title_indices)
            if not titel:
                continue
            unit_id, period_id = _row_ids(row)
            treffer.append(
                Treffer(
                    nummer=len(treffer) + 1,
                    titel=titel,
                    art=_cell_text(row, art_index) if art_index is not None else "",
                    unit_id=unit_id,
                    semester=(
                        _cell_text(row, semester_index)
                        if semester_index is not None
                        else ""
                    ),
                    lehrperson=_first_text(row, lehr_indices),
                    period_id=period_id,
                )
            )
        if treffer:
            return treffer
    return treffer


def _parse_zeitraum(text: str) -> tuple[str, str]:
    parts = re.split(r"\s*-\s*", text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


LABEL_FIELD_RE = re.compile(
    r'<div class="labelItemLine">\s*<label[^>]*>(.*?)</label>\s*'
    r'<div[^>]*class="answer[^"]*"[^>]*>(.*?)</div>',
    re.S | re.I,
)


def _strip_tags(text: str) -> str:
    return clean(re.sub(r"<[^>]+>", " ", text))


def _label_fields(html: str) -> dict[str, str]:
    felder: dict[str, str] = {}
    for match in LABEL_FIELD_RE.finditer(html):
        key = _strip_tags(match.group(1))
        if key and key not in felder:
            felder[key] = _strip_tags(match.group(2))
    return felder


def _selected_semester(html: str) -> str:
    select = re.search(
        r'<select[^>]*(?:termPeriodDropDownList|termSelect)[^>]*>(.*?)</select>',
        html,
        re.S | re.I,
    )
    if select:
        option = re.search(
            r"<option[^>]*selected[^>]*>(.*?)</option>", select.group(1), re.S | re.I
        )
        if option:
            return _strip_tags(option.group(1))
    return ""


def _parse_termine(parser: _PageParser) -> list[Termin]:
    termine: list[Termin] = []
    for table in parser.tables:
        rows = table.get("rows")
        if not isinstance(rows, list):
            continue
        header_index, headers = _header_row(rows)
        if header_index < 0:
            continue
        wochentag_index = _column(headers, "wochentag")
        raum_index = _column(headers, "raum")
        if wochentag_index is None and raum_index is None:
            continue
        rhythmus_index = _column(headers, "rhythmus")
        von_bis_index = _column(headers, "von - bis", "von-bis")
        start_index = _column(headers, "startdatum")
        for row in rows[header_index + 1 :]:
            if not row or row[0].get("tag") == "th":
                continue
            von, bis = (
                _parse_zeitraum(_cell_text(row, von_bis_index))
                if von_bis_index is not None
                else ("", "")
            )
            start, ende = (
                _parse_zeitraum(_cell_text(row, start_index))
                if start_index is not None
                else ("", "")
            )
            termine.append(
                Termin(
                    rhythmus=(
                        _cell_text(row, rhythmus_index)
                        if rhythmus_index is not None
                        else ""
                    ),
                    wochentag=(
                        _cell_text(row, wochentag_index)
                        if wochentag_index is not None
                        else ""
                    ),
                    von=von,
                    bis=bis,
                    start=start,
                    ende=ende,
                    raum=(
                        _cell_text(row, raum_index) if raum_index is not None else ""
                    ),
                )
            )
        if termine:
            return termine
    return termine


def parse_veranstaltung(html: str) -> Veranstaltung:
    parser = _parse_page(html)
    felder: dict[str, str] = {}
    for row in _table_rows(parser, "detail"):
        if len(row) >= 2:
            key = _cell_text(row, 0)
            if key:
                felder[key] = _cell_text(row, 1)
    for key, value in _label_fields(html).items():
        if value and not felder.get(key):
            felder[key] = value

    unit_raw = felder.get("Veranstaltungsnummer", "")
    unit_match = re.search(r"\d+", unit_raw)
    if unit_match:
        unit_id: int | None = int(unit_match.group(0))
    else:
        id_match = UNIT_ID_RE.search(html)
        unit_id = int(id_match.group(1)) if id_match else None
    veranstaltung = Veranstaltung(
        titel=felder.get("Titel", ""),
        art=felder.get("Veranstaltungsart", ""),
        semester=felder.get("Semester", "") or _selected_semester(html),
        lehrperson=(
            felder.get("Verantwortliche/r")
            or felder.get("Durchführende/r")
            or felder.get("Verantwortliche")
            or ""
        ),
        unit_id=unit_id,
    )
    veranstaltung.termine.extend(_parse_termine(parser))
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
    name: str = ""
    element_id: str = ""
    fields: list[tuple[str, str]] = field(default_factory=list)
    text_fields: list[str] = field(default_factory=list)
    password_fields: list[str] = field(default_factory=list)
    submit_fields: list[tuple[str, str]] = field(default_factory=list)

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
                name=values.get("name", ""),
                element_id=values.get("id", ""),
            )
            return
        if self._form is None:
            return
        if tag == "button":
            name = values.get("name", "")
            if name and values.get("type", "").lower() == "submit":
                self._form.submit_fields.append((name, values.get("value", "")))
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


def _forms(html: str) -> list[Formular]:
    parser = _FormParser()
    parser.feed(html)
    parser.close()
    return parser.forms


def parse_formular(html: str) -> Formular | None:
    forms = _forms(html)
    if not forms:
        return None
    for form in forms:
        if form.password_fields or form.text_fields:
            return form
    return forms[0]


def parse_suchformular(html: str) -> Formular | None:
    """Wählt das öffentliche Suchformular, nicht das Login-Formular im Kopf."""
    candidates = [
        form
        for form in _forms(html)
        if form.text_fields and not form.password_fields
    ]
    if not candidates:
        return None

    def score(form: Formular) -> int:
        identity = f"{form.element_id} {form.name} {form.action}".casefold()
        text = " ".join(form.text_fields).casefold()
        buttons = " ".join(name for name, _ in form.submit_fields).casefold()
        value = 0
        if "search" in identity:
            value += 6
        if "genericsearchmask" in identity:
            value += 4
        if "search" in text:
            value += 2
        if "search" in buttons or any(
            wert.casefold() == "suchen" for _, wert in form.submit_fields
        ):
            value += 2
        return value

    return max(candidates, key=score)


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
