# hisinone-cli

HISinOne-Campusportale im Terminal: öffentliches Vorlesungsverzeichnis ohne
Login, Stundenplan und Leistungsübersicht mit Login. Das Tool ist für viele
Hochschulen gedacht, die HISinOne einsetzen; erkundet und getestet wurde die
Instanz der Universität Freiburg.

## Schnellstart

```bash
pipx install git+https://github.com/smlfg/hisinone-cli
hisinone login
hisinone suche Oberseminar
hisinone veranstaltung "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung"
hisinone stundenplan --woche
hisinone noten
```

`hisinone login` fragt nach Portal-Adresse oder Hochschulname, Benutzer und
Passwort. Das Passwort wird verdeckt eingegeben und nicht gespeichert; die
Sitzung liegt in `~/.config/hisinone-cli/` mit Rechten 0600. Danach genügen
`hisinone whoami` und `hisinone logout` ohne Passwort. Die Portal-Adresse lässt
sich mit `HISINONE_BASE_URL` überschreiben, die Zugangsdaten mit
`HISINONE_USER` und `HISINONE_PASSWORD` (für Agenten).

Suche und Veranstaltungsdetails sind öffentlich und brauchen keinen Login.
`hisinone suche` nimmt den Suchbegriff positional, `hisinone veranstaltung`
den Namen. Bei mehreren Treffern fragt das Tool im Terminal nummeriert nach.
Ausgaben sind im Terminal lesbar; mit `--json` oder wenn stdout kein Terminal
ist, kommt JSON.

## Schritt 0: UX-Spec zuerst

Der komplette Ablauf steht in
[agent-learnings/WORKFLOW.md](https://github.com/smlfg/agent-learnings/blob/main/WORKFLOW.md).

1. Vor jeder Codezeile `docs/UX.md` ausfüllen: die wichtigsten
   Nutzer-Aufgaben als abtippbare Terminal-Sitzungen, dazu alle live
   erkundeten Routen und Fixtures unter `tests/fixtures/ux/`.
2. Spec prüfen: `python3 tests/harness/ux_spec.py docs/UX.md`
3. Gate nach dem Bau (beide müssen grün sein, sonst ist der Build nicht fertig):
   - `python3 tests/harness/ux_check.py .` (UX-Lint UX01–UX09)
   - `python3 tests/harness/ux_session.py .` (spielt die Sitzungen im
     Pseudo-Terminal gegen einen Fake-Server durch)

`tests/harness/` wird unverändert aus agent-learnings übernommen.

## Pflichtregel: Bedienbarkeit für Menschen

Jede CLI muss für Menschen bedienbar sein: `login`-Kommando statt nur Env,
Namen statt IDs, interaktive Bestätigung im TTY, `--confirm` nur für Agenten,
README-Schnellstart.

- `login` fragt im Terminal interaktiv (Passwort per getpass) und speichert
  im Schlüsselbund oder in einer Config-Datei mit 0600; dazu `logout` und
  `whoami` ohne Passwort-Ausgabe. Env-Variablen überschreiben die Config.
- Namen/Freitext positional (`hisinone suche Oberseminar`,
  `hisinone veranstaltung "…"`); mehrere Treffer → nummerierte Auswahl im TTY,
  ohne TTY Liste + Exit Usage.
- Schreibende Aktionen fragen im TTY „… verbindlich? [j/N]“ (Default Nein);
  `--confirm`/`--yes` nur für Agenten; ohne TTY und ohne Flag kein Request.
  `hisinone` hat derzeit keine schreibende Web-Aktion.
- Terminal-Ausgabe lesbar; JSON mit `--json` oder wenn stdout kein Terminal ist.
- Fehler nennen den nächsten Schritt, keine Tracebacks bei EOF/Strg+C/fehlender
  optionaler Abhängigkeit.
- README beginnt mit „Schnellstart“: `pipx install …`, Login, typische Befehle.
