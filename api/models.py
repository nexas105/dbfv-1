# Third Party
from rest_framework_api_key.models import AbstractAPIKey

# Django
from django.db import models


class ScopedAPIKey(AbstractAPIKey):
    """
    API key with a configurable write scope.

    A valid, active key may always read (safe HTTP methods). Writing
    (POST/PUT/PATCH/DELETE) additionally requires ``write_allowed``.
    """

    write_allowed = models.BooleanField(
        default=False,
        verbose_name='Schreibzugriff erlaubt',
        help_text='Erlaubt POST/PUT/PATCH/DELETE. Ohne Haken nur Lesezugriff.',
    )
    allowed_ips = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Erlaubte IPs',
        help_text='Kommagetrennte IPs oder CIDR-Bereiche (z. B. "203.0.113.5, '
        '198.51.100.0/24"). Leer = keine IP-Einschränkung.',
    )
    sensitive_access = models.BooleanField(
        default=False,
        verbose_name='Zugriff auf sensible Daten',
        help_text='Erlaubt Zugriff auf personen-/finanzbezogene Ressourcen '
        '(Bankkonten, Benutzerprofile, Rohanträge, interne Modelle). Ohne '
        'Haken nur Stammdaten und Lizenz-Endpoints.',
    )

    def ip_allowed(self, client_ip):
        """True if client_ip matches the allowlist (empty allowlist = allow all)."""
        # Standard Library
        import ipaddress

        if not self.allowed_ips.strip():
            return True
        try:
            addr = ipaddress.ip_address(client_ip)
        except ValueError:
            return False
        for entry in self.allowed_ips.split(','):
            entry = entry.strip()
            if not entry:
                continue
            try:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            except ValueError:
                continue
        return False

    class Meta(AbstractAPIKey.Meta):
        verbose_name = 'API-Key'
        verbose_name_plural = 'API-Keys'
