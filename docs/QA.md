# Pflicht-QA hisinone-cli

- Datum: 2026-10-31
- Version/Commit: 0.1.0, Commit `f8f59c9` (installiert via `pipx install git+https://github.com/smlfg/hisinone-cli`, Protokoll: `scratch/qa/pipx-install.log`)
- Prüfumgebung: pipx-Env `scratch/pipx` (Python 3.14.7), Aufruf ausschließlich über `PATH=$PWD/scratch/pipx/bin:$PATH`.
- Rolle: separater Prüfer (S5). Fehler im Code nicht gefixt, sondern belegt.

## Ergebnisübersicht

Zählung: **1 OK / 12 geprüft**, **11 FAIL**. Der vollständig gepackte/commitete Stand ist unbrauchbar:
Die installierte App stürzt bei **jedem** Befehl mit einem Python-Traceback ab
(`ModuleNotFoundError: No module named 'hisinone.cli'`), weil `src/hisinone/cli.py`,
`src/hisinone/__main__.py` und `tests/unit/test_cli.py` **nicht committet** sind
(`git ls-files src/hisinone/` enthält kein `cli.py`; im Arbeitsverzeichnis vorhanden,
aber untracked – pipx installiert jedoch den Commit, nicht das Arbeitsverzeichnis).

Verstöße gegen die Tool-Regeln: Tracebacks bei jedem Aufruf (auch `--help`, `--version`,
Strg+C/EOF nie erreichbar, da Import fehlschlägt), Exit-Code 1 statt definiertem
Usage-Fehler, `--version`/`--help` nicht mit Exit 0.

## Prüftabelle

| Prüfung | Befehl | Erwartet | Ergebnis | Beleg (gekürzt) |
|---|---|---|---|---|
| Q01 Frische Installation | `pipx install git+https://github.com/smlfg/hisinone-cli` | Installation erfolgreich, App `hisinone` verfügbar | OK | `scratch/qa/pipx-install.log`: „installed package hisinone-cli 0.1.0 … – hisinone“ |
| Q02 Version | `hisinone --version` | Version, Exit 0 | FAIL | `Traceback … from hisinone.cli import main` / `ModuleNotFoundError: No module named 'hisinone.cli'` (Exit 1) |
| Q03 Hilfe | `hisinone --help` | Hilfe, Exit 0 | FAIL | derselbe Traceback (Exit 1), `scratch/qa/q03-help.log` |
| Q04–Q05 Schnellstart-Zeilen (README) | `hisinone login`, `suche Oberseminar`, `veranstaltung "…"` (per `script` im Pseudo-Terminal, Protokolle `scratch/qa/q04-login.log`, `q05-suche.log`, `q06-veranstaltung.log`) | Prompt bzw. Ergebnisse im TTY | FAIL | bei allen derselbe Traceback; kein Prompt, keine Ausgabe |
| Q06 stundenplan | `hisinone stundenplan --woche` | Tischplan oder Hinweis auf `hisinone login`, Exit != 1 ohne Traceback | FAIL | derselbe Traceback, `scratch/qa/q07-stundenplan.log` |
| Q07 noten | `hisinone noten` | Leistungsübersicht oder Login-Hinweis | FAIL | derselbe Traceback, `scratch/qa/q08-noten.log` |
| Q08 login gegen Fake-Server (ux-routes) | `HISINONE_BASE_URL=http://127.0.0.1:<port> hisinone login` | interaktives Prompt, Strg+D/falsche Eingabe endet sauber | FAIL | Import-Crash vor jedem Prompt; Fake-Server-Ablauf nicht prüfbar, `scratch/qa/q09-login-fake.log` |
| Q09 Semantik live (Freiburg) | `hisinone suche Oberseminar` u. a. | plausible Treffer, Filter über alle Treffer geprüft | FAIL (blockiert) | wegen Q02–Q08 nicht ausführbar – Befehl endet vor Netz-Zugriff mit Traceback |
| Q10 Namensauflösung/Umlaute, leere Treffer | `hisinone suche "Algorithmen und Datenstrukturen"` | Auflösung mit Tippvarianten | FAIL (blockiert) | wie Q09 |
| Q11 Netz-Fehlerfall | `HISINONE_BASE_URL=http://127.0.0.1:1 hisinone suche X` | Meldung mit nächstem Schritt, kein Traceback | FAIL (blockiert) | wie Q09 |
| Q12 Bedienbarkeit (TTY → Text, JSON ohne TTY, Exit-Codes) | `hisinone suche Oberseminar > out.json` | JSON nur mit `--json`/nicht-TTY | FAIL (blockiert) | Import-Crash: Exit-Code-Verhalten nicht prüfbar |

## Tests gegen HEAD (Zusatzbeleg)

Nur zur Absicherung in einer sauberen HEAD-Worktree (seitdem gelöscht):
`pytest tests` in HEAD endet mit
`FAILED tests/acceptance/test_ux_sessions.py::test_login_speichert_sitzung`
(`AssertionError: Prompt 'Benutzer' nicht erschienen. Bisher:` – Import des fehlenden
`hisinone.cli`). 46/46 grüne Tests wie im UX-Gate-Bericht sind nur mit den
**uncommitteten** Dateien im Arbeitsverzeichnis reproduzierbar.

## Offene FAILs (Blocker)

1. `src/hisinone/cli.py` und `src/hisinone/__main__.py` committen (App-Entry fehlt im
   veröffentlichten Stand) – caused alle FAILs Q02–Q12.
2. `tests/unit/test_cli.py` committen (Unit-Tests der CLI fehlen in HEAD).
3. Nach Fix: komplette Wiederholung dieser QA, insbesondere Live-Checks (Q09–Q11)
   gegen https://campus.uni-freiburg.de/qisserver/… und Fake-Server-Login (Q08).
