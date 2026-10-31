# Schnittstelle: hisinone

Console-Script: `hisinone` (Package `hisinone`, Python >= 3.10).

Alle Befehle geben im Terminal lesbaren Text aus. Mit `--json` oder wenn stdout
kein Terminal ist (Pipe, Agent), steht auf stdout genau ein JSON-Objekt.
Prompts und Fehlermeldungen gehen nach stderr.

## Aufruf

```text
hisinone [--version] [--help]
hisinone [--json] login [PORTAL]
hisinone [--json] logout
hisinone [--json] whoami
hisinone [--json] suche BEGRIFF
hisinone [--json] veranstaltung NAME
hisinone [--json] stundenplan [--woche]
hisinone [--json] noten
```

`--json` ist global und wird auch nach dem Unterkommando akzeptiert.
`--version` und `--help` enden immer mit Exit-Code 0.

## Unterkommandos

### `login [PORTAL]`

Meldet sich an und speichert die Sitzung lokal.

- `PORTAL` (optional, positional): Portal-Adresse (`https://…`) oder
  Hochschulname. Ohne Argument und ohne `HISINONE_BASE_URL` fragt das Tool
  interaktiv nach der Adresse bzw. dem Hochschulnamen.
- Benutzer und Passwort: aus `HISINONE_USER` / `HISINONE_PASSWORD`, sonst
  interaktiv. Das Passwort wird per `getpass` verdeckt eingegeben und nie
  gespeichert oder geloggt.
- Login gilt erst als erfolgreich, wenn eine nur für angemeldete Personen
  sichtbare Seite geladen wurde.
- Shibboleth-/SSO-Portale werden nicht unterstützt. Meldung mit nächstem
  Schritt, Exit-Code 5.
- Ausgabe bei Erfolg: `Login erfolgreich`.
- Sitzungsdatei: `~/.config/hisinone-cli/session.json` (Verzeichnis 0700,
  Datei 0600). Es werden nur Cookies der HISinOne-Anwendung gespeichert.

### `logout`

Löscht die lokale Sitzungsdatei. Idempotent: ohne Sitzung Exit 0, Ausgabe
`Nicht angemeldet.`

### `whoami`

Zeigt Portal und angemeldete Person aus der gespeicherten Sitzung, ohne
Passwort. Ohne Sitzung Exit 4 mit Hinweis auf `hisinone login`.

### `suche BEGRIFF`

Öffentliche Veranstaltungssuche, kein Login nötig.

- `BEGRIFF` (Pflicht, positional): Sucht in Titel, Veranstaltungsnummer und
  Lehrperson.
- Ausgabe: nummerierte Treffer mit Titel, Veranstaltungsart und Unit-ID, z. B.
  `1) Oberseminar … (Veranstaltung 7586)`.
- Keine Treffer: Exit 0, Ausgabe `Keine Treffer.`
- Netzwerk-/Quellfehler: Exit 3.

### `veranstaltung NAME`

Öffentliche Detailansicht, kein Login nötig.

- `NAME` (Pflicht, positional): vollständiger oder eindeutiger
  Veranstaltungstitel, kein ID-Zwang.
- Ein Treffer: Ausgabe von Titel, Art, Semester, Lehrperson, Termin und Raum.
- Mehrere Treffer im TTY: nummerierte Auswahl per Eingabe.
- Mehrere Treffer ohne TTY: Liste plus Exit 2 (Usage) und Hinweis, den Namen
  genauer anzugeben.
- Keine Treffer: Exit 1 mit Hinweis, mit `hisinone suche BEGRIFF` zu suchen.

### `stundenplan [--woche]`

Zeigt den persönlichen Stundenplan, Login erforderlich.

- `--woche`: ganze Kalenderwoche. Ohne Flag: aktueller Tag.
- Bezugsdatum ist `HISINONE_HEUTE` (Format `JJJJ-MM-TT`, nur für Tests), sonst
  das heutige Datum.
- Ausgabe bei `--woche`:
  `Stundenplan KW 44 (26.10.2026 - 01.11.2026)` gefolgt von Terminen.
- Ohne oder mit abgelaufener Sitzung: Exit 4, Meldung nennt `hisinone login`.

### `noten`

Zeigt die Leistungsübersicht, Login erforderlich.

- Ausgabe: `Leistungsübersicht` gefolgt von Modul, Note und Status.
- Ohne oder mit abgelaufener Sitzung: Exit 4, Meldung nennt `hisinone login`.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg |
| 1 | Allgemeiner Fehler (unerwartete Antwort, Parse-Fehler, lokale Config defekt, keine Treffer bei `veranstaltung`) |
| 2 | Aufruf-/Usage-Fehler (fehlendes Argument, mehrdeutige Auswahl ohne TTY, fehlende Eingabe ohne TTY) |
| 3 | Netzwerk- oder Quellfehler (Timeout, HTTP-Status, nicht erreichbares Portal) |
| 4 | Login nötig oder Sitzung abgelaufen |
| 5 | Login fehlgeschlagen (falsche Zugangsdaten, SSO/Shibboleth nicht unterstützt) |

Usage-Fehler des Parsers liefern mit `--json` ebenfalls genau ein JSON-Objekt.
Bei Strg+C und EOF erscheint kein Traceback; der Exit-Code ist ungleich 0 und
die Meldung nennt den nächsten Schritt.

## JSON-Ausgabe

Mit `--json` bzw. nicht-interaktivem stdout steht genau ein Objekt auf stdout.
Prompts stehen nie in diesem Objekt.

```json
{"suche": "Oberseminar",
 "treffer": [{"nummer": 1,
              "titel": "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung",
              "art": "Seminar",
              "unit_id": 7586,
              "semester": "Wintersemester 2026/2027",
              "lehrperson": "Prof. Dr. A. Beispiel"}]}
```

```json
{"titel": "Oberseminar am Lehrstuhl Mustererkennung und Bildverarbeitung",
 "art": "Seminar",
 "semester": "Wintersemester 2026/2027",
 "lehrperson": "Prof. Dr. A. Beispiel",
 "unit_id": 7586,
 "termine": [{"rhythmus": "wöchentlich",
              "wochentag": "Di",
              "von": "16:00",
              "bis": "18:00",
              "start": "20.10.2026",
              "ende": "09.02.2027",
              "raum": "SR 02 017 (G.-Köhler-Allee 052)"}]}
```

```json
{"woche": {"kw": 44, "start": "26.10.2026", "ende": "01.11.2026"},
 "termine": [{"wochentag": "Mo", "von": "10:00", "bis": "12:00",
              "titel": "Algorithmen und Datenstrukturen", "raum": "HS 101"}]}
```

```json
{"leistungen": [{"modul": "Algorithmen und Datenstrukturen",
                 "pruefung": "Klausur",
                 "note": "1,7",
                 "status": "bestanden"}]}
```

```json
{"angemeldet": true,
 "portal": "https://campus.uni-freiburg.de",
 "benutzer": "max.mustermann@example.invalid"}
```

Fehlerobjekt:

```json
{"fehler": {"code": 4,
            "meldung": "Login fehlt.",
            "naechster_schritt": "hisinone login"}}
```

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `HISINONE_BASE_URL` | Überschreibt die Portal-Basis-URL (andere Hochschule, Fake-Server in Tests) |
| `HISINONE_USER` | Benutzername; überschreibt die interaktive Eingabe |
| `HISINONE_PASSWORD` | Passwort; nur für Agenten/Tests, wird nie gespeichert oder geloggt |
| `HISINONE_HEUTE` | Bezugsdatum `JJJJ-MM-TT` für `stundenplan`; nur für deterministische Tests, im Alltag gilt das heutige Datum |
| `XDG_CONFIG_HOME` | Basis für den Config-Pfad; Standard `~/.config` |

Ungültige Werte (z. B. unparsebares Datum, `NaN`, keine HTTP(S)-URL) führen zu
einem sauberen Fehler ohne Traceback.

## Config-Pfade

| Pfad | Inhalt | Rechte |
|---|---|---|
| `~/.config/hisinone-cli/` | Konfigurationsverzeichnis | 0700 |
| `~/.config/hisinone-cli/session.json` | Basis-URL, Zeitstempel, erlaubte HISinOne-Cookies | 0600 |

Passwörter, TOTP-Codes und Session-Cookies des Identity-Providers werden nie
gespeichert.
