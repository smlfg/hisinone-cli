"""HTTP-Client und Seitenabläufe für HISinOne."""

from __future__ import annotations

import datetime as dt
import http.cookiejar
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable

from . import parse
from .config import load_session
from .errors import HisinoneError, LoginFailed, LoginRequired, NetworkError, UsageError

DEFAULT_BASE_URL = (
    "https://campus.uni-freiburg.de/qisserver/pages/cs/sys/portal/"
    "hisinoneStartPage.faces"
)

START_PATH = "/qisserver/pages/cs/sys/portal/hisinoneStartPage.faces"

SEARCH_GET = (
    "/qisserver/pages/startFlow.xhtml"
    "?_flowId=searchCourseNonStaff-flow&_flowExecutionKey=e1s1"
)
DETAIL_URL = "/qisserver/pages/startFlow.xhtml"
TIMETABLE_URL = (
    "/qisserver/pages/cm/exa/timetable/myTimetable.xhtml"
    "?_flowId=showMyTimetable-flow"
)
GRADES_URL = (
    "/qisserver/pages/cm/exa/exam/myGrades.xhtml?_flowId=showMyGrades-flow"
)

PORTAL_NAMES = {
    "freiburg": DEFAULT_BASE_URL,
    "uni-freiburg": DEFAULT_BASE_URL,
    "universität freiburg": DEFAULT_BASE_URL,
    "universitaet freiburg": DEFAULT_BASE_URL,
    "albert-ludwigs-universität freiburg": DEFAULT_BASE_URL,
    "albert-ludwigs-universitaet freiburg": DEFAULT_BASE_URL,
}

EXCLUDED_COOKIE_PARTS = ("shibboleth", "_shib", "saml", "idp", "sso")


@dataclass
class Response:
    status: int
    text: str
    url: str


def normalize_base_url(value: str) -> str:
    text = (value or "").strip().rstrip("/")
    if not text:
        raise UsageError(
            "Portal-Adresse fehlt.", "hisinone login PORTAL oder HISINONE_BASE_URL setzen"
        )
    mapped = PORTAL_NAMES.get(text.casefold())
    if mapped:
        return mapped
    if "://" not in text:
        if re.search(r"[.\s]", text) or "/" in text:
            text = "https://" + text.lstrip("/")
        else:
            raise UsageError(
                f"Unbekannter Hochschulname: {value!r}.",
                "Portal-Adresse angeben, z. B. https://campus.example.invalid",
            )
    split = urllib.parse.urlsplit(text)
    if split.scheme not in {"http", "https"} or not split.netloc:
        raise UsageError(
            f"Keine gültige HTTP(S)-Portaladresse: {value!r}.",
            "Adresse im Format https://portal.example.invalid angeben",
        )
    return text


def resolve_portal(argument: str | None = None) -> str:
    if argument:
        return normalize_base_url(argument)
    from_env = os.environ.get("HISINONE_BASE_URL")
    if from_env:
        return normalize_base_url(from_env)
    return ""


def _cookie_key(domain: str) -> str:
    return domain.lstrip(".").casefold()


def _allowed_cookie(cookie: http.cookiejar.Cookie, host: str) -> bool:
    name = cookie.name.casefold()
    if any(part in name for part in EXCLUDED_COOKIE_PARTS):
        return False
    domain = _cookie_key(cookie.domain)
    if not domain:
        return True
    host = host.casefold()
    return host == domain or host.endswith("." + domain)


def _make_cookie(item: dict[str, object], host: str) -> http.cookiejar.Cookie:
    domain = str(item.get("domain") or host)
    return http.cookiejar.Cookie(
        version=0,
        name=str(item.get("name", "")),
        value=str(item.get("value", "")),
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=bool(item.get("domain")),
        domain_initial_dot=domain.startswith("."),
        path=str(item.get("path") or "/"),
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
    )


class HisinoneClient:
    def __init__(
        self,
        base_url: str,
        cookies: Iterable[dict[str, object]] | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        host = urllib.parse.urlsplit(self.base_url).hostname or ""
        self.host = host
        for item in cookies or []:
            if not isinstance(item, dict):
                continue
            if _allowed_cookie(_make_cookie(item, host), host):
                try:
                    self.jar.set_cookie(_make_cookie(item, host))
                except (ValueError, KeyError):
                    continue

    def start_url(self) -> str:
        split = urllib.parse.urlsplit(self.base_url)
        if split.path and split.path not in {"", "/"}:
            return self.base_url
        return self.base_url + START_PATH

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        base = self.base_url
        if not path.startswith("/"):
            path = "/" + path
        if base.endswith(".faces") or base.endswith(".xhtml"):
            return urllib.parse.urljoin(base, path)
        return base + path

    def request(
        self,
        method: str,
        path: str,
        data: list[tuple[str, str]] | None = None,
        referer: str | None = None,
    ) -> Response:
        url = self._url(path)
        body = None
        headers = {
            "User-Agent": "hisinone-cli/0.1 (+https://github.com/smlfg/hisinone-cli)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "de-DE,de;q=0.9",
        }
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if referer:
            headers["Referer"] = referer
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        try:
            with opener.open(request, timeout=self.timeout) as response:
                payload = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return Response(
                    status=int(response.status),
                    text=payload.decode(charset, "replace"),
                    url=response.geturl(),
                )
        except urllib.error.HTTPError as exc:
            payload = exc.read() if exc.fp is not None else b""
            charset = exc.headers.get_content_charset() if exc.headers else None
            return Response(
                status=int(exc.code),
                text=payload.decode(charset or "utf-8", "replace"),
                url=url,
            )
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise NetworkError(
                f"Portal nicht erreichbar: {reason}",
                "Verbindung prüfen oder HISINONE_BASE_URL anpassen",
            ) from exc

    def _expect_ok(self, response: Response) -> Response:
        if response.status >= 400:
            raise NetworkError(
                f"Portal antwortete mit HTTP {response.status}.",
                "Später erneut versuchen oder HISINONE_BASE_URL prüfen",
            )
        return response

    def search(self, begriff: str) -> list[parse.Treffer]:
        maske = self._expect_ok(self.request("GET", SEARCH_GET))
        form = parse.parse_formular(maske.text)
        if form is None:
            raise HisinoneError(
                "Suchformular nicht gefunden.",
                "Portal-Adresse prüfen oder hisinone suche erneut versuchen",
            )
        field = form.text_fields[0] if form.text_fields else None
        if field is None:
            raise HisinoneError(
                "Suchfeld nicht gefunden.",
                "Portal-Adresse prüfen oder hisinone suche erneut versuchen",
            )
        action = form.action or SEARCH_GET
        response = self._expect_ok(
            self.request(
                form.method.upper() or "POST",
                action,
                data=form.payload({field: begriff}),
                referer=maske.url,
            )
        )
        return parse.parse_suche(response.text)

    def veranstaltung(
        self, unit_id: int, period_id: int | None = None
    ) -> parse.Veranstaltung:
        query = {
            "_flowId": "detailView-flow",
            "unitId": str(unit_id),
            "navigationPosition": "courseoverviewShow",
        }
        if period_id is not None:
            query["periodId"] = str(period_id)
        response = self._expect_ok(
            self.request("GET", DETAIL_URL + "?" + urllib.parse.urlencode(query))
        )
        return parse.parse_veranstaltung(response.text)

    def _require_session(self) -> None:
        if load_session() is None:
            raise LoginRequired(
                "Login fehlt.", "hisinone login"
            )

    def _login_page(self, response: Response) -> bool:
        if "auth.login" in response.url or "auth.login" in response.text:
            return True
        form = parse.parse_formular(response.text)
        return bool(form and form.password_fields)

    def stundenplan(self) -> parse.Stundenplan:
        self._require_session()
        response = self.request("GET", TIMETABLE_URL)
        if response.status in {401, 403} or self._login_page(response):
            raise LoginRequired(
                "Sitzung abgelaufen oder Login fehlt.", "hisinone login"
            )
        self._expect_ok(response)
        return parse.parse_stundenplan(response.text)

    def noten(self) -> list[parse.Leistung]:
        self._require_session()
        response = self.request("GET", GRADES_URL)
        if response.status in {401, 403} or self._login_page(response):
            raise LoginRequired(
                "Sitzung abgelaufen oder Login fehlt.", "hisinone login"
            )
        self._expect_ok(response)
        return parse.parse_noten(response.text)

    def login(self, benutzer: str, passwort: str) -> dict[str, object]:
        start = self._expect_ok(self.request("GET", self.start_url()))
        if parse.ist_shibboleth(start.text) and "mobileLoginForm" not in start.text:
            raise LoginFailed(
                "Dieses Portal meldet nur über Shibboleth/SSO an.",
                "Portal-Adresse der HISinOne-Anmeldung verwenden",
            )
        form = parse.parse_formular(start.text)
        if form is None:
            raise LoginFailed(
                "Anmeldeformular nicht gefunden.",
                "Portal-Adresse prüfen oder hisinone login erneut versuchen",
            )
        if not form.password_fields:
            if parse.ist_shibboleth(start.text):
                raise LoginFailed(
                    "Dieses Portal meldet nur über Shibboleth/SSO an.",
                    "Portal-Adresse der HISinOne-Anmeldung verwenden",
                )
            raise LoginFailed(
                "Anmeldeformular ohne Passwortfeld.",
                "Portal-Adresse prüfen oder hisinone login erneut versuchen",
            )
        password_field = form.password_fields[0]
        user_field = form.text_fields[0] if form.text_fields else ""
        overrides = {password_field: passwort}
        if user_field:
            overrides[user_field] = benutzer
        action = form.action or self.base_url
        response = self.request(
            form.method.upper() or "POST",
            action,
            data=form.payload(overrides),
            referer=start.url,
        )
        if response.status in {401, 403}:
            raise LoginFailed(
                "Anmeldung abgelehnt.", "Zugangsdaten prüfen und hisinone login erneut"
            )
        self._expect_ok(response)
        text = response.text
        if parse.ist_shibboleth(text) and "Meine Funktionen" not in text:
            raise LoginFailed(
                "Dieses Portal meldet nur über Shibboleth/SSO an.",
                "Portal-Adresse der HISinOne-Anmeldung verwenden",
            )
        erfolg = (
            "Meine Funktionen" in text
            or "Angemeldet als" in text
            or "auth.logout" in text
        )
        if not erfolg:
            if re.search(r"(?i)(benutzername|passwort).{0,40}(falsch|ungültig|fehler)", text):
                raise LoginFailed(
                    "Benutzername oder Passwort falsch.",
                    "Zugangsdaten prüfen und hisinone login erneut",
                )
            raise LoginFailed(
                "Login nicht bestätigt: keine angemeldete Seite geladen.",
                "Zugangsdaten und Portal-Adresse prüfen",
            )
        benutzer_aus_seite = parse.parse_login_benutzer(text)
        cookies = [
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
            }
            for cookie in self.jar
            if _allowed_cookie(cookie, self.host)
        ]
        return {
            "portal": self.base_url,
            "benutzer": benutzer_aus_seite or benutzer,
            "zeitpunkt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "cookies": cookies,
        }


def client_for_portal(base_url: str, session: dict[str, object] | None = None) -> HisinoneClient:
    cookies = None
    if session and str(session.get("portal", "")).rstrip("/") == base_url.rstrip("/"):
        raw = session.get("cookies")
        if isinstance(raw, list):
            cookies = [item for item in raw if isinstance(item, dict)]
    return HisinoneClient(base_url, cookies=cookies)
