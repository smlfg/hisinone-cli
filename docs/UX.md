# UX-Spec: hisinone

`hisinone` macht HISinOne-Campusportale im Terminal nutzbar. Das öffentliche
Vorlesungsverzeichnis (Suche und Veranstaltungsdetails) funktioniert ohne
Login. Stundenplan und Leistungsübersicht brauchen eine angemeldete Sitzung.

Erkundet wurde die Instanz der Universität Freiburg:
`https://campus.uni-freiburg.de/qisserver/pages/cs/sys/portal/hisinoneStartPage.faces`.
Die Live-Erkundung erfolgte ausschließlich lesend per GET; die Notizen und
Rohantworten liegen unter `scratch/live/`. Die Suche ist ein JSF-Formular und
wird per POST abgeschickt. Dieser POST wurde bei der Erkundung nicht an den
echten Server gesendet. Die Trefferliste in
`tests/fixtures/ux/suche_oberseminar.html` ist deshalb aus den live geladenen
Katalog- und Detailseiten zusammengesetzt und im Fixture als solche markiert.
Antworten von Login-Seiten (Login-Erfolg, Stundenplan, Noten) sind synthetisch
und ebenfalls im Fixture markiert.

## Meta

```ux-meta
{"tool": "hisinone",
 "install": "pipx install git+https://github.com/smlfg/hisinone-cli",
 "base_url_env": "HISINONE_BASE_URL",
 "env": {"HISINONE_HEUTE": "2026-10-31"},
 "credential_env": ["HISINONE_USER", "HISINONE_PASSWORD"]}
```

`HISINONE_BASE_URL` überschreibt die Portal-Adresse (für den Fake-Server in den
Tests). `HISINONE_HEUTE` setzt das Bezugsdatum für `stundenplan --woche` und
dient nur deterministischen Tests; im Alltag gilt das heutige Datum.

## Sitzungen

### Installation und Login

Beim ersten Start fragt `login` nach Portal-Adresse oder Hochschulname,
Benutzername und Passwort. Das Passwort wird verdeckt eingegeben und nicht
gespeichert. Die Sitzung liegt in `~/.config/hisinone-cli/` mit Rechten 0600.
Ist `HISINONE_BASE_URL` gesetzt, entfällt die Portal-Frage. Die Zugangsdaten
im Beispiel sind erfunden.

```ux-session
$ pipx install git+https://github.com/smlfg/hisinone-cli
$ hisinone login
< Benutzer:
> max.mustermann@example.invalid
< Passwort:
> geheim
< Login erfolgreich
! exit 0
```

### Veranstaltungen nach Namen suchen

Der Suchbegriff ist positional und wird gegen Titel, Nummer und Lehrperson
gesucht. Die Treffer sind nummeriert; die Ausgabe nennt Titel, Veranstaltungsart
und die Unit-ID, damit `veranstaltung` direkt damit weiterarbeiten kann.

```ux-session
$ hisinone suche Oberseminar
< 1) Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung (Veranstaltung 7586)
< 2) Oberseminar am Lehrstuhl Programmiersprachen (Veranstaltung 7578)
< 3) Oberseminar am Lehrstuhl Rechnernetze und Telematik (Veranstaltung 7589)
! exit 0
```

### Veranstaltungsdetails anzeigen

`veranstaltung` nimmt den Namen positional. Bei mehreren Treffern fragt das
Tool im Terminal nummeriert nach; der Name wird nicht als ID verlangt. Die
Detailansicht zeigt Titel, Art, Semester, Lehrperson, Termin und Raum.

```ux-session
$ hisinone veranstaltung "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung"
< Titel: Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung
< Art: Seminar
< Semester: Wintersemester 2026/2027
< Lehrperson: Prof. Dr. A. Beispiel
< Termin: Di 16:00-18:00, 20.10.2026-09.02.2027
< Raum: SR 02 017 (G.-Köhler-Allee 052)
! exit 0
```

### Stundenplan der Woche

`stundenplan --woche` braucht eine gespeicherte Login-Sitzung. Ohne Sitzung
nennt der Fehler den nächsten Schritt: `hisinone login`. Das Bezugsdatum kommt
aus `HISINONE_HEUTE`, sonst aus dem heutigen Tag.

```ux-session
$ hisinone stundenplan --woche
< Stundenplan KW 44 (26.10.2026 - 01.11.2026)
< Mo 10:00-12:00 Algorithmen und Datenstrukturen (HS 101)
< Di 16:00-18:00 Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung (SR 02 017)
! exit 0
```

### Leistungsübersicht

`noten` zeigt die Leistungen der angemeldeten Person. Auch hier gilt: ohne
Login verweist die Fehlermeldung auf `hisinone login`.

```ux-session
$ hisinone noten
< Leistungsübersicht
< Algorithmen und Datenstrukturen: 1,7 (bestanden)
< Programmiersprachen: 2,3 (bestanden)
! exit 0
```

## Lesende Routen

Die Routen bilden alle Requests der Sitzungen gegen den Fake-Server ab. Die
öffentliche Suche ist ein POST auf das JSF-Formular; sie ist lesend und löst
keine schreibende Aktion aus. Login-only-Seiten sind synthetisch, weil ohne
Zugangsdaten keine echte Anmeldung erfolgt. `path` wird ohne Querystring
verglichen, `query_contains` unterscheidet die Flow-Varianten.

```ux-routes
[{"method":"GET","path":"/qisserver/pages/cs/sys/portal/hisinoneStartPage.faces","response":"tests/fixtures/ux/startseite.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"POST","path":"/qisserver/rds","query_contains":"category=auth.login","response":"tests/fixtures/ux/login_erfolg.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/qisserver/pages/startFlow.xhtml","query_contains":"searchCourseNonStaff-flow","response":"tests/fixtures/ux/suchmaske.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"POST","path":"/qisserver/pages/startFlow.xhtml","query_contains":"searchCourseNonStaff-flow","response":"tests/fixtures/ux/suche_oberseminar.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/qisserver/pages/startFlow.xhtml","query_contains":"detailView-flow","response":"tests/fixtures/ux/veranstaltung_7586.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/qisserver/pages/cm/exa/timetable/myTimetable.xhtml","query_contains":"showMyTimetable-flow","response":"tests/fixtures/ux/stundenplan.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/qisserver/pages/cm/exa/exam/myGrades.xhtml","query_contains":"showMyGrades-flow","response":"tests/fixtures/ux/noten.html","status":200,"content_type":"text/html; charset=utf-8"}]
```

## Keine schreibende Aktion

`hisinone` bietet bewusst keine Prüfungsanmeldung, keine Belegung und keine
anderen schreibenden Web-Aktionen. Deshalb gibt es keinen `ux-formsteps`-Block
und keine `[j/N]`-Bestätigung. `login` und `logout` verändern nur die lokale
Sitzungsdatei.
