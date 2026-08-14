# Changelog

Alle relevanten Änderungen an diesem Projekt werden hier festgehalten.

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
