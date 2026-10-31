from pathlib import Path

from hisinone import parse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ux"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_suche_liefert_drei_treffer():
    treffer = parse.parse_suche(_fixture("suche_oberseminar.html"))
    assert len(treffer) == 3
    assert treffer[0].titel.endswith("Mustererkennung und Bildverarbeitung")
    assert treffer[0].art == "Seminar"
    assert treffer[0].unit_id == 7586
    assert treffer[0].semester == "Wintersemester 2026/2027"
    assert treffer[0].lehrperson == "Prof. Dr. A. Beispiel"
    assert treffer[2].unit_id == 7589


def test_veranstaltung_parst_details_und_termine():
    veranstaltung = parse.parse_veranstaltung(_fixture("veranstaltung_7586.html"))
    assert veranstaltung.titel.endswith("Mustererkennung und Bildverarbeitung")
    assert veranstaltung.art == "Seminar"
    assert veranstaltung.semester == "Wintersemester 2026/2027"
    assert veranstaltung.lehrperson == "Prof. Dr. A. Beispiel"
    assert veranstaltung.unit_id == 7586
    assert len(veranstaltung.termine) == 1
    termin = veranstaltung.termine[0]
    assert (termin.wochentag, termin.von, termin.bis) == ("Di", "16:00", "18:00")
    assert (termin.start, termin.ende) == ("20.10.2026", "09.02.2027")
    assert termin.raum == "SR 02 017 (G.-Köhler-Allee 052)"


def test_stundenplan_liefert_kopf_und_termine():
    plan = parse.parse_stundenplan(_fixture("stundenplan.html"))
    assert plan.ueberschrift == "Stundenplan KW 44 (26.10.2026 - 01.11.2026)"
    assert len(plan.termine) == 3
    assert plan.termine[0] == {
        "wochentag": "Mo",
        "von": "10:00",
        "bis": "12:00",
        "titel": "Algorithmen und Datenstrukturen",
        "raum": "HS 101",
    }


def test_noten_parst_alle_leistungen():
    leistungen = parse.parse_noten(_fixture("noten.html"))
    assert [(item.modul, item.note, item.status) for item in leistungen] == [
        ("Algorithmen und Datenstrukturen", "1,7", "bestanden"),
        ("Programmiersprachen", "2,3", "bestanden"),
    ]


def test_suchformular_wird_erkannt():
    formular = parse.parse_formular(_fixture("suchmaske.html"))
    assert formular is not None
    assert formular.method == "post"
    assert formular.text_fields == ["genericSearchMask:search:inputField_0"]
    namen = dict(formular.fields)
    assert namen["javax.faces.ViewState"] == "e1s1"
    assert namen["genericSearchMask:search:termSelect_input"] == "eq|2|2026"


def test_loginformular_und_marker():
    formular = parse.parse_formular(_fixture("startseite.html"))
    assert formular is not None
    assert formular.password_fields == ["fdsa"]
    assert formular.text_fields == ["asdf"]
    assert parse.parse_login_benutzer(_fixture("login_erfolg.html")).startswith(
        "Max Mustermann"
    )
    assert parse.ist_shibboleth("<html>Shibboleth Identity Provider</html>")
    assert not parse.ist_shibboleth(_fixture("startseite.html"))
