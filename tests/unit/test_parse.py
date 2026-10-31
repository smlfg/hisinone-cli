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


LIVE_SUCHMASKE = """<!DOCTYPE html>
<html><body>
<form id="mobileLoginForm" name="mobileLoginForm" method="post"
      action="/qisserver/rds?state=user&type=1&category=auth.login">
  <input name="asdf" type="text">
  <input name="fdsa" type="password">
</form>
<form id="genericSearchMask" name="genericSearchMask" method="post"
      action="/qisserver/pages/startFlow.xhtml?_flowId=searchCourseNonStaff-flow&amp;_flowExecutionKey=e1s1">
  <input type="hidden" name="javax.faces.ViewState" value="e1s1">
  <input name="genericSearchMask:search:inputField_0" type="text" value="">
  <button type="submit" name="genericSearchMask:buttonsBottom:search" value=" "></button>
  <button type="submit" name="genericSearchMask:buttonsBottom:search" value="Suchen">Suchen</button>
</form>
</body></html>
"""

LIVE_SUCHERGEBNIS = """<!DOCTYPE html>
<html><body>
<table class="tableOverflowFix" role="presentation"><tr><td>
<table id="genSearchRes:table" class="tableWithBorder table">
  <tr>
    <th class="actionsLeft column0"></th>
    <th>Nummer</th>
    <th>Semesterunabhängiger Titel</th>
    <th>Semesterabhängiger Titel</th>
    <th>Semester</th>
    <th>Veranstaltungsart</th>
    <th>Lehrsprache</th>
    <th>Verantwortliche Lehrperson</th>
    <th>Durchführende Lehrperson</th>
    <th>Organisationseinheit</th>
    <th>Aktionen</th>
  </tr>
  <tr>
    <td></td><td>04LE57S-Beispiel</td>
    <td>Oberseminar Beispiel</td><td>Oberseminar Beispiel</td>
    <td>WS 2026</td><td>Seminar</td><td>deutsch</td>
    <td>Prof. Dr. A. Beispiel</td><td>Prof. Dr. B. Beispiel</td>
    <td>Beispielinstitut</td>
    <td><a href="/qisserver/pages/startFlow.xhtml?_flowId=detailView-flow&amp;unitId=123&amp;periodId=456&amp;navigationPosition=searchCourses">Details</a></td>
  </tr>
</table>
</td></tr></table>
</body></html>
"""

LIVE_DETAIL = """<!DOCTYPE html>
<html><body>
<a href="/qisserver/pages/startFlow.xhtml?_flowId=detailView-flow&amp;unitId=42&amp;periodId=456">Permalink</a>
<div class="labelItemLine"><label for="a">Titel </label><div id="a" class="answer">Oberseminar Beispiel </div></div>
<div class="labelItemLine"><label for="b">Veranstaltungsart </label><div id="b" class="answer textBold">Seminar </div></div>
<div class="labelItemLine"><label for="c">Verantwortliche/r </label><div id="c" class="answer textBold"><ul><li><span>Prof. Dr. A. Beispiel</span></li></ul></div></div>
<select id="detailViewData:termPeriodDropDownList_input">
  <option value="456" selected="selected">Wintersemester 2026/2027</option>
</select>
<table class="tableOverflowFix"><tr><td>
<table id="detailViewData:appointmentSeriesTable">
  <tr>
    <th>Änderungen</th><th>Rhythmus</th><th>Wochentag</th><th>Von - Bis</th>
    <th>Ausfalltermin</th><th>Startdatum - Enddatum</th><th>Erw. Tn.</th>
    <th>Bemerkung</th><th>Durchführende/r</th><th>Raum</th>
  </tr>
  <tr>
    <td></td><td>wöchentlich</td><td>Di</td><td>16:00 - 18:00</td><td></td>
    <td>20.10.2026 - 09.02.2027</td><td></td><td></td>
    <td>Prof. Dr. A. Beispiel</td><td>SR 02 017</td>
  </tr>
</table>
</td></tr></table>
</body></html>
"""


def test_suchformular_waehlt_suche_statt_login():
    formular = parse.parse_suchformular(LIVE_SUCHMASKE)
    assert formular is not None
    assert formular.element_id == "genericSearchMask"
    assert formular.text_fields == ["genericSearchMask:search:inputField_0"]
    assert ("genericSearchMask:buttonsBottom:search", "Suchen") in formular.submit_fields


def test_suche_parst_verschachtelte_live_tabelle():
    treffer = parse.parse_suche(LIVE_SUCHERGEBNIS)
    assert len(treffer) == 1
    assert treffer[0].titel == "Oberseminar Beispiel"
    assert treffer[0].art == "Seminar"
    assert treffer[0].semester == "WS 2026"
    assert treffer[0].lehrperson == "Prof. Dr. A. Beispiel"
    assert (treffer[0].unit_id, treffer[0].period_id) == (123, 456)


def test_veranstaltung_parst_live_labels_und_termine():
    veranstaltung = parse.parse_veranstaltung(LIVE_DETAIL)
    assert veranstaltung.titel == "Oberseminar Beispiel"
    assert veranstaltung.art == "Seminar"
    assert veranstaltung.semester == "Wintersemester 2026/2027"
    assert veranstaltung.lehrperson == "Prof. Dr. A. Beispiel"
    assert veranstaltung.unit_id == 42
    assert len(veranstaltung.termine) == 1
    termin = veranstaltung.termine[0]
    assert (termin.wochentag, termin.von, termin.bis) == ("Di", "16:00", "18:00")
    assert (termin.start, termin.ende) == ("20.10.2026", "09.02.2027")
    assert termin.raum == "SR 02 017"


def test_client_suche_nutzt_suchformular_und_abschickknopf():
    from hisinone.client import HisinoneClient

    client = HisinoneClient("https://portal.example.invalid")
    requests = []

    def fake_request(method, path, data=None, referer=None):
        requests.append((method, path, data))
        if method == "GET":
            return type("Response", (), {"status": 200, "text": LIVE_SUCHMASKE, "url": path})()
        return type("Response", (), {"status": 200, "text": LIVE_SUCHERGEBNIS, "url": path})()

    client.request = fake_request  # type: ignore[assignment]
    treffer = client.search("Oberseminar")
    assert len(treffer) == 1
    assert treffer[0].titel == "Oberseminar Beispiel"
    method, _, data = requests[1]
    assert method == "POST"
    assert ("genericSearchMask:buttonsBottom:search", "Suchen") in data
    assert (
        "genericSearchMask:search:inputField_0",
        "Oberseminar",
    ) in data
