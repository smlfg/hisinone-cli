# Pflicht-QA hisinone-cli

- Datum: 2026-10-31
- Version/Commit: 0.1.0, Commit `f1baad6` (Nachprüfung nach Fix; Q01-Protokoll aus der ersten Runde)
- Prüfumgebung: frisches venv `scratch/ux-venv` (Python 3.13), Aufruf über `scratch/ux-venv/bin/hisinone`; volles UX-Gate `ux_check.py` und `ux_session.py` jeweils Exit 0.
- Rolle: separater Prüfer (S5), Fixes und Nachprüfung (S6). Die Nachprüfung erfolgte live lesend gegen die Freiburger HISinOne-Instanz sowie gegen den Fake-Server aus `tests/harness/`.

## Ergebnisübersicht

Zählung: **12 OK / 12 geprüft**, **0 FAIL**. Die frühere Ursache ist behoben:
`src/hisinone/cli.py`, `src/hisinone/__main__.py` und `tests/unit/test_cli.py`
sind seit Commit `a41442b` versioniert; die App startet damit nach frischer
Installation. Bei der Live-Nachprüfung zusätzlich gefundene Parserfehler
(Login-Formular statt Suchformular, verschachtelte Ergebnistabellen,
Live-Labels der Detailseite) wurden in Commit `f1baad6` mit Unit-Tests behoben.

## Prüftabelle

| Prüfung | Befehl | Erwartet | Ergebnis | Beleg (gekürzt) |
|---|---|---|---|---|
| Q01 Frische Installation | `pipx install git+https://github.com/smlfg/hisinone-cli` | Installation erfolgreich, App `hisinone` verfügbar | OK | `scratch/qa/pipx-install.log`: „installed package hisinone-cli 0.1.0 … – hisinone“ |
| Q02 Version | `hisinone --version` | Version, Exit 0 | OK (nach Fix `a41442b`) | `hisinone 0.1.0`, Exit 0 |
| Q03 Hilfe | `hisinone --help` | Hilfe, Exit 0 | OK (nach Fix `a41442b`) | Hilfe mit 7 Unterkommandos, Exit 0 |
| Q04–Q05 Schnellstart-Zeilen (README) | `hisinone login`, `suche Oberseminar`, `veranstaltung "…"` (per `script` im Pseudo-Terminal) | Prompt bzw. Ergebnisse im TTY | OK (nach Fix `a41442b`/`f1baad6`) | Login-Prompt erscheint; Suche und Detailansicht liefern Text im TTY, Exit 0 |
| Q06 stundenplan | `hisinone stundenplan --woche` | Stundenplan oder Hinweis auf `hisinone login`, Exit != 1 ohne Traceback | OK (nach Fix `a41442b`) | `{"fehler":{"code":4,…,"naechster_schritt":"hisinone login"}}`, Exit 4 |
| Q07 noten | `hisinone noten` | Leistungsübersicht oder Login-Hinweis | OK (nach Fix `a41442b`) | `{"fehler":{"code":4,…,"naechster_schritt":"hisinone login"}}`, Exit 4 |
| Q08 login gegen Fake-Server (ux-routes) | `HISINONE_BASE_URL=http://127.0.0.1:<port> hisinone login` | interaktives Prompt, Strg+D/falsche Eingabe endet sauber | OK (nach Fix `a41442b`) | `ux_session.py`: „Installation und Login PASS“; Prompt `Benutzer`/`Passwort`, Sitzungsdatei 0600 |
| Q09 Semantik live (Freiburg) | `hisinone suche Oberseminar` u. a. | plausible Treffer, Filter über alle Treffer geprüft | OK (nach Fix `f1baad6`) | Live 10 nummerierte Treffer mit Titel, Art, Semester, Unit-ID; Ausgabe im TTY als Text |
| Q10 Namensauflösung/Umlaute, leere Treffer | `hisinone suche "Algorithmen und Datenstrukturen"`; `hisinone suche Algorithmen` | Auflösung mit Tippvarianten, leere Treffer sauber | OK (nach Fix `f1baad6`) | `Algorithmen` liefert 3 Treffer (u. a. „Algorithmentheorie“); die exakte Phrase liefert live 0 Treffer und wird als `Keine Treffer.`/leere Liste mit Exit 0 ausgegeben |
| Q11 Netz-Fehlerfall | `HISINONE_BASE_URL=http://127.0.0.1:1 hisinone suche X` | Meldung mit nächstem Schritt, kein Traceback | OK (nach Fix `f1baad6`) | Code 3, Meldung „Portal nicht erreichbar …“, nächster Schritt „Verbindung prüfen oder HISINONE_BASE_URL anpassen“ |
| Q12 Bedienbarkeit (TTY → Text, JSON ohne TTY, Exit-Codes) | `hisinone suche Oberseminar > out.json` bzw. im Pseudo-Terminal | JSON nur mit `--json`/nicht-TTY | OK (nach Fix `f1baad6`) | Ohne TTY genau ein JSON-Objekt; im TTY nummerierte Texttreffer, kein JSON |

## Tests gegen HEAD (Nachprüfung)

`scratch/venv/bin/pytest -q` gegen den Arbeitsstand: **50 passed**.
`python3 tests/harness/ux_check.py .`: **PASS** (UX00–UX08, UX09 SKIP, Exit 0).
`python3 tests/harness/ux_session.py .`: **PASS** (alle fünf Sitzungen, Exit 0).
Beide Läufe installieren frisch aus dem Repo und nutzen ausschließlich den
Fake-Server; Live-Aufrufe der Nachprüfung waren lesend und sind in
`scratch/qa/s6-live-summary.json` zusammengefasst.

## Offene Punkte

Keine offenen FAILs. Die Live-Suche ist ein lesender JSF-POST; es gibt keinen
reinen GET-Suchendpunkt. Die Nachprüfung wurde nicht gepusht (Commit `f1baad6`
liegt nur lokal).
