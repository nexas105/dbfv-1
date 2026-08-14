# DBFV REST-API

## Warum diese API

Das Antragssystem des DBFV e.V. verwaltet Starter-, Studio- und
Kampfrichterlizenzen. Bislang lag der Datenzugriff ausschließlich in der
Weboberfläche und im Django-Admin.

Der **DBFV NRW** (Landesverband) benötigt **programmatischen Zugriff** auf diese
Daten, um eigene Anwendungen und Automatisierungen anzubinden (z. B. Auslesen
von Anträgen, Studios und Stammdaten für Verbandsprozesse). Diese API schafft
dafür eine definierte, abgesicherte Schnittstelle.

Ziel dieses Beitrags ist es, **initial bei der Entwicklung zu helfen** und eine
solide, erweiterbare Basis zu legen: Authentifizierung, klare Endpunkt-Struktur
und ein pro Schlüssel steuerbarer Schreibzugriff. Feinere Rechte und schreibende
Antrags-Workflows können darauf aufbauend ergänzt werden.

## Authentifizierung

Jeder Zugriff braucht einen **API-Key** im HTTP-Header:

```
Authorization: Api-Key <PREFIX.SCHLUESSEL>
```

- Ohne gültigen Key: `403 Forbidden`.
- Lesen (`GET`) von Stammdaten/Lizenz-Endpoints ist mit jedem gültigen Key möglich.
- Schreiben (`POST`/`PUT`/`PATCH`/`DELETE`) erfordert zusätzlich `write_allowed`.
- **Sensible Ressourcen** (Bankkonten, Benutzerprofile, interne Modelle, die
  Roh-Antrags-CRUD-Endpoints und der **Massen-Export** `/licenses/valid/`)
  erfordern zusätzlich das Flag `sensitive_access`. Ohne dieses Flag sieht ein
  Key nur Stammdaten (Gyms, Bundesländer, Länder) und den datensparsamen
  Lizenz-Lookup `/licenses/lookup/`.
- **Rate-Limit:** standardmäßig 1000 Anfragen/Stunde, gezählt **pro API-Key**
  (nicht pro IP).
- Bereits **vor der Key-Prüfung** gilt zusätzlich ein IP-Limit von 120
  Anfragen/Minute (`API_PREAUTH_RATE_LIMIT`). Dadurch werden auch ungültige
  oder ständig wechselnde Key-Präfixe begrenzt.

### IP-Allowlist (Zweit-Absicherung für Server-zu-Server)

Optional lässt sich ein Key auf feste Quell-IPs beschränken (Feld `allowed_ips`,
kommagetrennte IPs oder CIDR-Bereiche). Ist die Liste leer, gilt keine
Einschränkung. Passt die Anfrage-IP nicht, antwortet die API mit `403`.

> Hinweis: Für Server-zu-Server ist eine **IP-Allowlist** die richtige
> Zusatzsicherung — der HTTP-`Origin`-Header greift nur bei Browsern (CORS) und
> wird von S2S-Clients i. d. R. nicht gesetzt.
>
> **Client-IP-Ermittlung (wichtig):** `X-Forwarded-For` ist client-fälschbar
> und wird **standardmäßig ignoriert** — es zählt `REMOTE_ADDR` (korrekt für
> direkten Apache/gunicorn-Betrieb). Nur wenn die Anwendung hinter einem oder
> mehreren vertrauenswürdigen Reverse-Proxies läuft, wird
> `API_TRUSTED_PROXY_COUNT` in den Settings auf die Anzahl dieser Proxies
> gesetzt; dann wird der entsprechende Eintrag von rechts aus der
> `X-Forwarded-For`-Kette genommen. Ist die Kette kürzer als erwartet, wird
> fail-closed abgelehnt. Der Proxy muss eingehende `X-Forwarded-For`-Header
> überschreiben (nicht anhängen).

### Key anlegen

Im Django-Admin unter **API-Keys**, oder per Shell:

```python
from api.models import ScopedAPIKey

obj, key = ScopedAPIKey.objects.create_key(
    name="nrw-integration",
    write_allowed=False,
    sensitive_access=False,        # True für Bank-/Personen-/Rohantragsdaten
    allowed_ips="203.0.113.0/24",  # optional, leer lassen für keine IP-Schranke
)
print(key)  # wird nur EINMAL angezeigt; danach ist nur der Hash gespeichert
```

Den zurückgegebenen `key` sicher verwahren — er lässt sich nicht erneut
auslesen.

Das öffentliche Formular zur Beantragung eines Keys ist separat auf fünf
POST-Anfragen pro Stunde und Client-IP begrenzt (`API_KEY_REQUEST_RATE_LIMIT`).
Beide IP-basierten Limits verwenden dieselbe vertrauenswürdige
Client-IP-Ermittlung wie die Allowlist.

## Endpunkte

Basis: `/api/v1/`

| Ressource | Pfad |
|---|---|
| Studios | `/api/v1/gym/` |
| Bundesländer | `/api/v1/state/` |
| Länder | `/api/v1/country/` |
| Bankkonten | `/api/v1/bankaccount/` |
| Manager-Emails | `/api/v1/manageremail/` |
| Email-Cron | `/api/v1/emailcron/` |
| Benutzerprofile | `/api/v1/userprofile/` |
| Anträge Starter | `/api/v1/submissionstarter/` |
| Anträge International | `/api/v1/submissioninternational/` |
| Anträge Studio | `/api/v1/submissiongym/` |
| Anträge Kampfrichter | `/api/v1/submissionjudge/` |

Jede Ressource bietet Standard-CRUD (Liste, Detail, Anlegen, Ändern, Löschen).
Listen sind paginiert (`PAGE_SIZE = 50`).

### Beispiel

```bash
curl -H "Authorization: Api-Key 2VvDXE8I.xxxxxxxx" \
     http://127.0.0.1:8000/api/v1/gym/
```

## Lizenz-Endpoints (Kernfall NRW)

Eine „Lizenz" ist ein bewilligter Antrag für ein Kalenderjahr.
**Gültig = Status „Bewilligt" UND `creation_date.year == Jahr`** (Standard:
laufendes Jahr, per `?year=` überschreibbar).

### Alle gültigen Lizenzen (Massen-Export)

```
GET /api/v1/licenses/valid/?year=2026&type=starter&page=1&page_size=100
```

- **Erfordert `sensitive_access`** — es ist ein Personendaten-Export.
- `year` optional (Standard: laufendes Jahr)
- `type` optional: `starter` | `international` | `judge` | `studio`
- **Paginiert** (`page`, `page_size`; Standard 100, Maximum 500).
- Felder minimal. `date_of_birth` wird **nur** mit `?include=date_of_birth`
  mitgeliefert (Datensparsamkeit).

Antwort (paginiert):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "license_type": "starter",
      "label": "Starterlizenz",
      "id": 42,
      "name": "Mustermann, Max",
      "year": 2026,
      "valid": true
    }
  ]
}
```

### Gültigkeit gezielt abfragen (Lookup, datensparsam)

```
POST /api/v1/licenses/lookup/
Content-Type: application/json

{
  "last_name": "Mustermann",
  "date_of_birth": "1990-05-01",
  "year": 2026
}
```

Parameter (mindestens **zwei** angeben): `last_name`, `first_name`, `email`,
`date_of_birth` (`YYYY-MM-DD`), `year` (optional).

- Die Identifikatoren werden ausschließlich im JSON-Body übertragen. `GET` ist
  deaktiviert, damit Namen, E-Mail-Adressen und Geburtsdaten nicht in URLs oder
  üblichen Access-Logs landen.
- Der POST ist semantisch read-only und benötigt kein `write_allowed`.
- Datenschutz: gibt **keine Personendaten** zurück, nur ob eine gültige Lizenz
  existiert (Typ + Jahr).
- Die Zwei-Feld-Pflicht verhindert Enumeration (z. B. Geburtsdaten durchprobieren).
- Ein Typ wird nur geprüft, wenn er **mindestens zwei** der angegebenen Felder
  besitzt: Starter/International (alle vier), Kampfrichter (Name/E-Mail, kein
  Geburtsdatum), Studio (nur E-Mail → per Lookup nicht auffindbar, nur im
  Massen-Export).
- Mit `< 2` Feldern: `400`.

Antwort:

```json
{
  "year": 2026,
  "valid": true,
  "matches": [
    { "license_type": "starter", "label": "Starterlizenz", "year": 2026, "valid": true }
  ]
}
```

### Interaktive Doku / Schema

- Swagger-UI: `GET /api/v1/docs/`
- ReDoc: `GET /api/v1/redoc/`
- OpenAPI-Schema (JSON/YAML): `GET /api/v1/schema/`

## Webhooks

Eine Änderungsbenachrichtigung per Webhook (Push an eine NRW-URL bei
Statuswechsel) ist geplant, aber **bewusst nicht Teil dieser API**. Grund:
synchroner Outbound-Versand, SSRF-Fläche und der Versand von Personendaten an
Dritte brauchen erst eine saubere Lösung (asynchrone Queue mit Retry,
SSRF-Schutz, DSGVO-Klärung). Kommt in einem eigenen PR.

## Betrieb / TLS

TLS wird von diesem Repository **nicht** bereitgestellt (die mitgelieferte
Apache-Konfiguration lauscht auf `:80`). HTTPS muss vom Reverse-Proxy des
Betreibers (z. B. Coolify) terminiert werden.

- Standard ist HTTP-tauglich (keine erzwungenen Secure-Cookies/Redirects), damit
  ein HTTP-only-Betrieb nicht ausgesperrt wird.
- Sobald TLS sicher terminiert ist: `DJANGO_SECURE=1` setzen. Dann greifen
  Secure-Cookies, HSTS, SSL-Redirect und die Auswertung von `X-Forwarded-Proto`.
- Der Proxy muss eingehende `X-Forwarded-Proto`/`X-Forwarded-For`-Header
  überschreiben. Vor dem Aktivieren `python manage.py check --deploy` ausführen.

## Protokollierung / Audit

Jeder API-Zugriff wird über den Logger `dbfv.audit` protokolliert (Standard:
stdout): Key-Präfix, Client-IP, Methode, Pfad, Statuscode; `403`/`429` als
Warnung, Key-Widerrufe im Admin ebenfalls. **Nicht** protokolliert werden das
Key-Secret, der Request-Body und die Query-Zeichenkette (mögliche Suchdaten) —
geloggt wird nur `request.path` ohne Query. Im Deployment kann der Logger auf
eine Datei oder einen Collector umgeleitet werden.

## Grenzen / offene Punkte

- Schreibende Zugriffe auf Anträge (`submission*`) können zusätzliche Felder
  benötigen, die das Modell als nicht editierbar markiert (z. B. `user`). Der
  primäre Anwendungsfall ist derzeit Lesen; Serializer sind bei Bedarf zu
  erweitern.
- `write_allowed` ist ein einzelnes Flag pro Key, kein feingranulares
  Rollen-/Rechtemodell. Für differenzierte Rechte pro Ressource ist ein Ausbau
  vorgesehen.
