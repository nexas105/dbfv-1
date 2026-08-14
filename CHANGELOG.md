# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt
- REST-API unter `/api/v1/` auf Basis von Django REST Framework, inklusive
  OpenAPI-Schema (`/api/v1/schema/`), Swagger-UI (`/api/v1/docs/`) und ReDoc
  (`/api/v1/redoc/`) via drf-spectacular.
- API-Key-Authentifizierung (`djangorestframework-api-key`) mit eigenem
  Key-Modell `ScopedAPIKey` und pro Key konfigurierbaren Rollen/Scopes:
  - `write_allowed` – Schreibzugriff (`POST`/`PUT`/`PATCH`/`DELETE`); ohne Flag
    nur Lesezugriff, ohne gültigen Key kein Zugriff.
  - `sensitive_access` – Zugriff auf sensible Ressourcen (Bankkonten,
    Benutzerprofile, interne Modelle, Roh-Antrags-CRUD und den Massen-Export).
  - `allowed_ips` – optionale IP-/CIDR-Allowlist als Zweit-Absicherung für
    Server-zu-Server-Zugriffe.
  Keys sind im Django-Admin verwaltbar (Django-Admin unter `/admin/`
  aktiviert – war zuvor nicht eingebunden).
- CRUD-Endpunkte für alle Modelle (Gym, State, Country, BankAccount,
  ManagerEmail, EmailCron, UserProfile, Submission*) mit Filter (`?feld=wert`),
  Volltextsuche (`?search=`), Sortierung (`?ordering=`) und Pagination.
- Lizenz-Endpoints. „Gültig" = Status Bewilligt im laufenden Kalenderjahr:
  - `/api/v1/licenses/lookup/` – datensparsame, gezielte Gültigkeitsabfrage:
    mindestens zwei Identifikatoren (Name/E-Mail/Geburtsdatum) nötig, Rückgabe
    nur Typ/Jahr/gültig, kein Rückgeben von Personendaten (gegen Enumeration).
  - `/api/v1/licenses/valid/` – Massen-Export, nur mit `sensitive_access`;
    paginiert (`page`/`page_size`, max. 500), minimale Felder, `date_of_birth`
    nur mit `?include=date_of_birth`.
- Öffentliches Formular „API-Key beantragen" (kleiner Footer-Link) mit
  Honeypot-Spamschutz; Anfragen gehen per E-Mail an die Manager-Adressen.
- `API.md` mit Hintergrund und Nutzungsanleitung zur API.

### Sicherheit
- Rate-Limiting: pro API-Key (Standard 1000/Stunde) plus vorgelagertes
  IP-Limit vor der Key-Prüfung (`API_PREAUTH_RATE_LIMIT`, Standard 120/Minute);
  das Beantragungsformular ist zusätzlich pro IP begrenzt
  (`API_KEY_REQUEST_RATE_LIMIT`).
- IP-Allowlist gegen `X-Forwarded-For`-Spoofing gehärtet: XFF wird
  standardmäßig ignoriert (nur `REMOTE_ADDR`), Proxy-Betrieb ausschließlich über
  `API_TRUSTED_PROXY_COUNT` (fail-closed).
- Produktions-Settings sicher als Standard: `DEBUG=False`, Clickjacking-Schutz
  (`X-Frame-Options: DENY`), `SECURE_CONTENT_TYPE_NOSNIFF`.
- HTTPS-Härtung (Secure-Cookies, HSTS, SSL-Redirect) als Gesamt-Opt-in über
  `DJANGO_SECURE=1`. TLS wird vom Repository nicht garantiert (die mitgelieferte
  Apache-Konfiguration lauscht auf `:80`) und muss vom Reverse-Proxy des
  Betreibers terminiert werden. Der Proxy-TLS-Header (`X-Forwarded-Proto`) wird
  **nur** bei gesetztem `DJANGO_SECURE=1` ausgewertet, damit ohne
  vertrauenswürdigen TLS-Proxy kein `https` vorgetäuscht werden kann.
- IDOR bei Kampfrichteranträgen behoben (Owner-/Berechtigungsprüfung in der
  Detail-View, analog zu Starter/International/Studio).
- Berechtigungsprüfungen in gemeinsamen Submission-Views leiten Rechte aus dem
  konkreten Modell ab (`delete_<model>` / `change_<model>`) statt fixer
  Modellnamen.
- CSV-Exporte gegen Spreadsheet-Formula-Injection neutralisiert.
- „PDF erneut senden" nur noch per POST mit CSRF-Schutz (vorher GET).
- Audit-Logging aller API-Zugriffe (Logger `dbfv.audit`): Key-Präfix, IP,
  Methode, Pfad, Status; `403`/`429` und Key-Widerrufe als Warnung. Ohne
  Key-Secret, Request-Body oder Query-Zeichenkette (keine Suchdaten).
