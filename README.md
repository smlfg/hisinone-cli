# hisinone-cli

HISinOne-Campusportale im Terminal: öffentliches Vorlesungsverzeichnis ohne
Login, Stundenplan und Leistungsübersicht mit Login. Erkundet und getestet wurde
die Instanz der Universität Freiburg; über `HISINONE_BASE_URL` lässt sich jede
andere HISinOne-Instanz ansprechen.

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
Sitzung liegt in `~/.config/hisinone-cli/` mit Rechten 0600. Ist
`HISINONE_BASE_URL` gesetzt, entfällt die Portal-Frage.

## Befehle

### Suchen und Details (öffentlich)

```bash
hisinone suche Oberseminar
hisinone suche "Algorithmen und Datenstrukturen"
hisinone veranstaltung "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung"
```

`suche` nimmt den Suchbegriff positional und durchsucht Titel, Nummer und
Lehrperson. Die Treffer sind nummeriert und nennen die Unit-ID.
`veranstaltung` nimmt den Namen positional. Bei mehreren Treffern fragt das
Tool im Terminal nummeriert nach; ohne Terminal erscheint die Liste mit
Exit-Code 2.

### Stundenplan und Leistungen (Login)

```bash
hisinone stundenplan
hisinone stundenplan --woche
hisinone noten
```

`stundenplan --woche` zeigt die aktuelle Kalenderwoche, ohne Flag den heutigen
Tag. Ohne Sitzung nennen die Befehle den nächsten Schritt: `hisinone login`.

### Sitzung

```bash
hisinone whoami
hisinone logout
```

`whoami` zeigt Portal und angemeldete Person ohne Passwort. `logout` löscht die
lokale Sitzungsdatei und ist idempotent.

## Konfiguration

| Variable | Bedeutung |
|---|---|
| `HISINONE_BASE_URL` | Portal-Basis-URL überschreiben (andere Hochschule, Fake-Server) |
| `HISINONE_USER` | Benutzername für Agenten/Tests |
| `HISINONE_PASSWORD` | Passwort für Agenten/Tests, wird nie gespeichert |
| `HISINONE_HEUTE` | Bezugsdatum `JJJJ-MM-TT` für `stundenplan`, nur für Tests |

Die Sitzung liegt unter `~/.config/hisinone-cli/session.json` (0600). Es werden
nur Cookies der HISinOne-Anwendung gespeichert, keine Zugangsdaten.

## Ausgabe

Im Terminal erscheinen lesbare Zeilen. Mit `--json` oder wenn stdout kein
Terminal ist, steht genau ein JSON-Objekt auf stdout; Prompts und Fehler gehen
nach stderr. Details und Feldnamen stehen in [INTERFACE.md](INTERFACE.md).

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg |
| 1 | Allgemeiner Fehler (unerwartete Antwort, Parse-Fehler, kein Treffer) |
| 2 | Usage-Fehler (fehlendes Argument, mehrdeutige Auswahl ohne TTY) |
| 3 | Netzwerk- oder Quellfehler |
| 4 | Login nötig oder Sitzung abgelaufen |
| 5 | Login fehlgeschlagen (Zugangsdaten, SSO/Shibboleth) |

## Hinweis

`hisinone` ist ein inoffizielles Werkzeug und kein Angebot der Hochschulen.
Es nutzt keine offizielle API; Änderungen am Portal können die Auswertung
brechen. Live wurden ausschließlich lesende GET-Requests auf öffentliche
Seiten gesendet. Das Tool bietet bewusst keine schreibenden Web-Aktionen wie
Prüfungsanmeldung oder Belegung.

Die Anforderungen stehen in [ANFORDERUNGEN.md](ANFORDERUNGEN.md), die
Schnittstelle in [INTERFACE.md](INTERFACE.md), die UX-Spezifikation in
[docs/UX.md](docs/UX.md).

## Lizenz

MIT, siehe [LICENSE](LICENSE).
