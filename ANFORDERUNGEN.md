# Anforderungen: hisinone-cli

## Zweck

`hisinone` macht HISinOne-Campusportale im Terminal nutzbar. Studierende und
andere Hochschulangehörige finden Veranstaltungen, sehen Termine und Räume und
prüfen nach dem Login ihren Stundenplan und ihre Leistungen. Das Tool ist für
die vielen Hochschulen gedacht, die HISinOne einsetzen; erkundet und getestet
wurde die Instanz der Universität Freiburg.

## Nutzer-Aufgaben

1. **Einrichten und anmelden.** `hisinone login` fragt interaktiv nach
   Portal-Adresse oder Hochschulname, Benutzer und Passwort. Das Passwort wird
   verdeckt eingegeben und nie gespeichert. Danach zeigen `hisinone whoami` und
   `hisinone logout` den Sitzungszustand, ohne das Passwort erneut zu verlangen.
2. **Veranstaltungen suchen.** `hisinone suche BEGRIFF` durchsucht das
   öffentliche Vorlesungsverzeichnis nach Titel, Nummer und Lehrperson. Die
   Treffer nennen Titel, Veranstaltungsart und Unit-ID.
3. **Veranstaltungsdetails lesen.** `hisinone veranstaltung NAME` zeigt Titel,
   Art, Semester, Lehrperson, Termine und Räume. Bei mehreren Treffern wird im
   Terminal nummeriert ausgewählt; im nicht-interaktiven Betrieb erscheint die
   Liste mit Exit-Code 2.
4. **Stundenplan der Woche sehen.** `hisinone stundenplan --woche` braucht eine
   gespeicherte Login-Sitzung und zeigt die Termine der Kalenderwoche.
5. **Leistungen prüfen.** `hisinone noten` zeigt die Leistungsübersicht der
   angemeldeten Person.

## Nachfrage

- Quelle: `./scratch/ref/NEXT20.md`, Stand 30.10.2026 (Nachfrage-Check nach
  demand-first-gate: gh-Suche, Glama, modelcontextprotocol/servers-Issues,
  Web/Reddit, curl von der Box).
- Ergebnis: GO. Der Bedarf ist belegt, die Schnittstelle ist erreichbar, und
  die Konkurrenz ist gering: nur `hisinone-mcp` (★1). Es gibt kein etabliertes
  CLI mit vergleichbarer Abdeckung.
- Einschränkung: hisinone.hs-mannheim.de und his.hs-heilbronn.de waren von der
  Box nicht erreichbar. Die Live-Erkundung erfolgte lesend über die öffentliche
  Instanz `campus.uni-freiburg.de`.

## Datenquelle

- Öffentliches Vorlesungsverzeichnis der Universität Freiburg:
  `https://campus.uni-freiburg.de/qisserver/pages/cs/sys/portal/hisinoneStartPage.faces`.
- HISinOne ist an vielen Hochschulen im Einsatz. Die Basis-URL ist deshalb über
  `HISINONE_BASE_URL` überschreibbar (Fake-Server in Tests, andere Hochschulen).
- Suche und Detailansicht sind öffentlich und lesend. Die Suche ist ein
  JSF-POST-Formular; ein reiner GET-Suchendpunkt existiert nicht.
- Login, Stundenplan und Noten benötigen eine angemeldete Sitzung. Die
  Antworten dafür sind in den Tests synthetisch, weil keine Zugangsdaten
  vorliegen.
- Rohantworten und Notizen der Erkundung liegen unter `scratch/live/`.

## Grenzen

- **Inoffiziell.** Das Tool ist kein Angebot der Hochschulen und nutzt keine
  offizielle API. Änderungen am Portal können die Auswertung brechen.
- **Nur lesend live getestet.** Live wurden ausschließlich lesende GET-Requests
  auf öffentliche Seiten gesendet. Der Such-POST und alle Login-Antworten
  wurden gegen den Fake-Server geprüft, nicht gegen den echten Server.
- **Keine schreibenden Web-Aktionen.** Es gibt bewusst keine Prüfungsanmeldung,
  keine Belegung und keine Bestätigungsfrage mit `[j/N]`. `login` und `logout`
  verändern nur die lokale Sitzungsdatei.
- **Kein Shibboleth-SSO.** Portale, die ausschließlich über einen
  Identity-Provider anmelden, werden nicht unterstützt; das Tool meldet das
  klar und nennt den nächsten Schritt.
- **Keine Zugangsdaten im Repo.** Passwörter werden weder gespeichert noch
  geloggt noch als CLI-Flag angenommen. Die Sitzung liegt in
  `~/.config/hisinone-cli/` mit Rechten 0600.
