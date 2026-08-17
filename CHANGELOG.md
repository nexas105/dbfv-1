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

### Behoben
- Review-Fixes zu PR #157 (automatischer Copilot-Review):
  - Scope-Umgehung geschlossen: `DELETE` erfordert jetzt `sensitive_access`.
    Zuvor konnte ein reiner Schreib-Key offene Stammdaten (Gym/State/Country)
    löschen, deren `CASCADE` sensible Anträge mitgelöscht hätte
    (`api/permissions.py`).
  - Submission-Endpoints (`SubmissionStarter/International/Gym/Judge`) sind jetzt
    read-only: `POST` lief zuvor in einen `IntegrityError` (Feld `user`
    `editable=False`, unter API-Key-Auth kein Request-User) und `PATCH` auf den
    Status umging den Fach-Workflow (z. B. Gym-Aktivierung bei Bewilligung)
    (`api/views.py`).
  - CSV-Formula-Injection-Schutz (`csv_safe`) jetzt auch in den TSV-Exporten
    `submission/views/submissions.py` und `submission/views/gym.py`; zuvor nur in
    `BaseCsvExportView`.
  - „API-Key beantragen"-Formular meldet Erfolg nur noch bei tatsächlich
    zugestellter E-Mail. Zuvor wurde auch ohne Empfänger oder bei Zustellfehler
    (`fail_silently=True`) „übermittelt" gemeldet und die Anfrage verworfen;
    jetzt `fail_silently=False`, Fehler/leerer Empfängerkreis werden über
    `dbfv.audit` geloggt und dem Absender als Fehlermeldung gezeigt
    (`api/contact.py`).
  - OpenAPI-Schema stimmt jetzt mit den tatsächlichen Responses überein:
    Envelope-Serializer für `licenses/lookup/` (`{year, valid, matches}`) und
    `licenses/valid/` (`{count, next, previous, results}`) statt eines bloßen
    Arrays; generierte Clients deserialisieren wieder korrekt (`api/licenses.py`).
  - OpenAPI-Security-Scheme (`ApiKeyAuth`, Header `Authorization: Api-Key …`)
    deklariert und global auf alle Operationen angewandt; zuvor beschrieb das
    Schema geschützte Endpunkte ohne den nötigen Header
    (`dbfv/settings_global.py`).
  - Massen-Export `licenses/valid/` paginiert jetzt auf DB-Ebene (Count +
    Fenster-Slice pro Modell) statt erst alle Zeilen aller vier Tabellen in den
    Speicher zu laden (`api/licenses.py`).
  - Audit-Middleware ist wieder äußerste Middleware (vor `CommonMiddleware`),
    damit `APPEND_SLASH`-Redirects (301) und direkt von `CommonMiddleware`
    erzeugte Antworten mit dem client-sichtbaren Status geloggt werden
    (`dbfv/settings_global.py`).

## [Unreleased] — Antragsseiten Design 2.0

Mehrstufige Antragsformulare (Wizard) für Starter- und Internationale Anträge.
Der Antrag wird weiterhin in **einem** POST abgeschickt; die Schritte sind rein
clientseitig (CSS/JS). Serverseitige Django-Validierung bleibt unverändert.

### Geändert
- `submission/templates/base.html`
  Wizard-Styles zum „Design 2.0"-Style-Layer ergänzt (Stepper, Schritt-Karten,
  Navigation).
- `submission/forms.py`
  `SubmissionStarterForm` und `SubmissionInternationalForm`: crispy-Layout in
  benannte Wizard-Schritte (`Div` mit `data-step`) gegliedert; Absenden-Button
  als `wizard-submit` markiert (wird erst im letzten Schritt sichtbar).
- `submission/templates/submission/starter/create.html`
  Seite als 4-Schritt-Wizard (Studio → Persönliches → Wettkampf → Bestätigung).
  Wettkampfregeln/Anti-Doping/DSGVO in ein Bootstrap-Modal verschoben (Link im
  Bestätigungs-Schritt). Zustimmungs-Checkboxen (`terms_and_conditions`,
  `data_protection`) starten per JS deaktiviert und werden erst freigeschaltet,
  wenn der Modal-Text bis ans Ende gescrollt wurde. Sichtbare Bestätigung des
  gewählten Studios (`aria-live`); Auto-Scroll bei Studioauswahl entfernt.
- `submission/forms.py` (Nachtrag)
  `SubmissionStarterForm`: Hinweis + Modal-Link (`#legalModal`) im
  Bestätigungs-Schritt ergänzt.
- `submission/templates/tags/wizard.html` (Nachtrag)
  Dekorative Pfeil-Icons `aria-hidden`; Absenden prüft den letzten Schritt.
- `submission/templates/submission/international/create.html`
  Seite als 4-Schritt-Wizard analog zum Starter-Antrag.

### Hinzugefügt
- `submission/templates/tags/wizard.html`
  Wiederverwendbare Wizard-Navigation (Zurück/Weiter) + Steuerungs-JS.
- `submission/templates/tags/studio_picker.html`
  Neue Studioauswahl: direkte Vereins-/Studiosuche (Name/Ort), optionaler
  Bundesland-Filter mit Anzahl der Vereine je Land, Studios als anklickbare
  Cards (Radios, barrierefrei). Ersetzt das alte Accordion in Starter- und
  Internationalem Antrag. Natives `gym`-Feld bleibt als noscript-Fallback.

### Geändert (2. Iteration)
- `submission/forms.py`
  „Ihr Studio"-Zwischenüberschrift entfernt; `_tune_submission_widgets`
  ergänzt: `date`-Eingaben für Geburtsdatum (+ Meisterschaftsdatum international),
  `tel`-Feld, numerische `inputmode`/`min`/`max`/`step` für PLZ/Größe/Gewicht.
  Damit greift die client-seitige Validierung pro Wizard-Schritt.
- `submission/templates/submission/starter/create.html`
  Accordion → `studio_picker`-Include; Studio-JS ins Include verschoben.
- `submission/templates/submission/international/create.html`
  Accordion → `studio_picker`-Include; zusätzlich vorgeschalteter Wizard-Schritt
  „Voraussetzungen" mit Pflicht-Bestätigung, bevor das Formular erscheint.
