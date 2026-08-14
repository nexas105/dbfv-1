# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# Django
from django.core.cache import cache
from django.test import RequestFactory, override_settings

# dbfv
from api.models import ScopedAPIKey
from submission.models import Country


class ScopedAPIKeyPermissionTest(APITestCase):
    """Read for any valid key; write only with write_allowed."""

    @classmethod
    def setUpTestData(cls):
        _, cls.rw = ScopedAPIKey.objects.create_key(name='rw', write_allowed=True)
        _, cls.ro = ScopedAPIKey.objects.create_key(name='ro', write_allowed=False)
        Country.objects.create(name='Germany')

    def _auth(self, key):
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {key}')

    def test_no_key_denied(self):
        self.assertEqual(self.client.get('/api/v1/country/').status_code, status.HTTP_403_FORBIDDEN)

    def test_read_only_key_can_read(self):
        self._auth(self.ro)
        self.assertEqual(self.client.get('/api/v1/country/').status_code, status.HTTP_200_OK)

    def test_read_only_key_cannot_write(self):
        self._auth(self.ro)
        res = self.client.post('/api/v1/country/', {'name': 'France'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_write_key_can_write(self):
        self._auth(self.rw)
        res = self.client.post('/api/v1/country/', {'name': 'France'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Country.objects.filter(name='France').exists())

    def test_submission_endpoint_is_read_only(self):
        # Submissions expose no write actions (user field editable=False,
        # status changes must run through the domain workflow).
        _, key = ScopedAPIKey.objects.create_key(
            name='sw', write_allowed=True, sensitive_access=True
        )
        self._auth(key)
        res = self.client.post('/api/v1/submissionstarter/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_requires_sensitive_access(self):
        # DELETE on open Stammdaten cascades into sensitive submissions.
        self._auth(self.rw)
        country = Country.objects.create(name='Italy')
        res = self.client.delete(f'/api/v1/country/{country.pk}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_ip_allowlist_blocks_foreign_ip(self):
        _, key = ScopedAPIKey.objects.create_key(name='ip', allowed_ips='10.0.0.1')
        self._auth(key)
        res = self.client.get('/api/v1/country/', REMOTE_ADDR='203.0.113.9')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_ip_allowlist_permits_listed_cidr(self):
        _, key = ScopedAPIKey.objects.create_key(name='ip2', allowed_ips='203.0.113.0/24')
        self._auth(key)
        res = self.client.get('/api/v1/country/', REMOTE_ADDR='203.0.113.9')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_forged_forwarded_for_is_ignored_by_default(self):
        # No trusted proxy configured -> X-Forwarded-For must not grant access.
        _, key = ScopedAPIKey.objects.create_key(name='ip3', allowed_ips='10.0.0.1')
        self._auth(key)
        res = self.client.get(
            '/api/v1/country/',
            REMOTE_ADDR='203.0.113.9',
            HTTP_X_FORWARDED_FOR='10.0.0.1',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_exact_filter(self):
        Country.objects.create(name='Spain')
        self._auth(self.ro)
        res = self.client.get('/api/v1/country/', {'name': 'Spain'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

    def test_search(self):
        Country.objects.create(name='Spain')
        self._auth(self.ro)
        res = self.client.get('/api/v1/country/', {'search': 'pai'})
        self.assertEqual([c['name'] for c in res.data['results']], ['Spain'])

    def test_ordering(self):
        Country.objects.create(name='Austria')
        self._auth(self.ro)
        res = self.client.get('/api/v1/country/', {'ordering': 'name'})
        names = [c['name'] for c in res.data['results']]
        self.assertEqual(names, sorted(names))

    @override_settings(API_PREAUTH_RATE_LIMIT='2/minute')
    def test_invalid_keys_are_rate_limited_before_permissions(self):
        cache.clear()
        for prefix in ('AAAA0001', 'BBBB0002'):
            res = self.client.get(
                '/api/v1/country/',
                HTTP_AUTHORIZATION=f'Api-Key {prefix}.invalid',
                REMOTE_ADDR='203.0.113.50',
            )
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.get(
            '/api/v1/country/',
            HTTP_AUTHORIZATION='Api-Key CCCC0003.invalid',
            REMOTE_ADDR='203.0.113.50',
        )
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Retry-After', res)


class SensitiveScopeTest(APITestCase):
    def test_sensitive_model_needs_scope(self):
        _, plain = ScopedAPIKey.objects.create_key(name='plain')
        _, priv = ScopedAPIKey.objects.create_key(name='priv', sensitive_access=True)

        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {plain}')
        self.assertEqual(
            self.client.get('/api/v1/bankaccount/').status_code, status.HTTP_403_FORBIDDEN
        )
        # non-sensitive Stammdaten stay open
        self.assertEqual(self.client.get('/api/v1/country/').status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {priv}')
        self.assertEqual(
            self.client.get('/api/v1/bankaccount/').status_code, status.HTTP_200_OK
        )


class ThrottleKeyTest(APITestCase):
    def test_cache_key_uses_key_prefix_not_secret(self):
        # dbfv
        from api.throttling import APIKeyRateThrottle

        throttle = APIKeyRateThrottle()

        class _Req:
            META = {'HTTP_AUTHORIZATION': 'Api-Key ABCD1234.longsecretvalue'}

        cache_key = throttle.get_cache_key(_Req(), None)
        self.assertIn('ABCD1234', cache_key)
        self.assertNotIn('longsecretvalue', cache_key)


class ApiKeyRequestFormTest(APITestCase):
    # Note: the view is exercised live; a Client-based render test hits a
    # Python 3.14 x Django 5.1 bug in the test client's template
    # instrumentation (Context.__copy__), unrelated to this code. We test the
    # only non-trivial logic — the honeypot — directly on the form.
    def _data(self, **over):
        data = {
            'name': 'Max', 'organization': 'DBFV NRW', 'email': 'max@nrw.de',
            'intended_use': 'Lizenzabgleich', 'website': '',
        }
        data.update(over)
        return data

    def setUp(self):
        cache.clear()

    def test_valid_without_honeypot(self):
        # dbfv
        from api.contact import ApiKeyRequestForm

        self.assertTrue(ApiKeyRequestForm(data=self._data()).is_valid())

    def test_honeypot_blocks_spam(self):
        # dbfv
        from api.contact import ApiKeyRequestForm

        self.assertFalse(ApiKeyRequestForm(data=self._data(website='http://spam')).is_valid())

    @override_settings(API_KEY_REQUEST_RATE_LIMIT='2/hour')
    def test_post_is_rate_limited_by_ip(self):
        # RequestFactory avoids the Python 3.14/Django 5.1 test-client
        # template instrumentation bug documented above.
        from django.contrib.auth.models import AnonymousUser

        from api.contact import api_key_request

        payload = self._data(website='http://spam')
        factory = RequestFactory()
        responses = []
        for _ in range(3):
            request = factory.post(
                '/api-key/anfrage', payload, REMOTE_ADDR='203.0.113.8'
            )
            request.user = AnonymousUser()
            responses.append(api_key_request(request))
        self.assertEqual(responses[0].status_code, 200)
        self.assertEqual(responses[1].status_code, 200)
        response = responses[2]
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Retry-After', response)


class SchemaTest(APITestCase):
    def test_schema_public(self):
        # Schema/docs are served without an API key.
        res = self.client.get('/api/v1/schema/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)


def _make_starter(dob='1990-05-01', submission_status='2'):
    """Create a SubmissionStarter with all required relations."""
    # Django
    from django.contrib.auth.models import User

    # dbfv
    from submission.models import BankAccount, Country, Gym, State, SubmissionStarter

    bank = BankAccount.objects.create(owner_name='DBFV', iban='DE00', bic='X', bank_name='Bank')
    state = State.objects.create(name='NRW', short_name='NRW', bank_account=bank)
    gym = Gym.objects.create(name='Muscle Gym', state=state)
    country = Country.objects.create(name='Germany')
    user = User.objects.create(username=f'u{dob}{submission_status}')
    return SubmissionStarter.objects.create(
        user=user, date_of_birth=dob, active_since='2010', last_name='Mustermann',
        first_name='Max', street='Weg', house_nr='1', zip_code=12345, city='Köln',
        tel_number='0', email='m@x.de', nationality=country, height=180, weight=80,
        category='1', terms_and_conditions=True, gym=gym,
        submission_status=submission_status,
    )


class LicenseEndpointTest(APITestCase):
    def setUp(self):
        _, self.plain = ScopedAPIKey.objects.create_key(name='lic')
        _, self.priv = ScopedAPIKey.objects.create_key(name='lic-priv', sensitive_access=True)
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.plain}')

    def test_bulk_needs_sensitive_scope(self):
        # plain key: bulk export forbidden
        self.assertEqual(
            self.client.get('/api/v1/licenses/valid/').status_code, status.HTTP_403_FORBIDDEN
        )

    def test_valid_lists_approved_with_sensitive_key(self):
        _make_starter(submission_status='2')
        _make_starter(dob='1985-01-01', submission_status='1')  # Eingegangen -> not valid
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.priv}')
        res = self.client.get('/api/v1/licenses/valid/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # paginated response
        self.assertEqual(res.data['count'], 1)
        result = res.data['results'][0]
        self.assertEqual(result['license_type'], 'starter')
        # minimal by default: no date_of_birth unless requested
        self.assertNotIn('date_of_birth', result)

    def test_valid_includes_dob_only_on_request(self):
        _make_starter(dob='1990-05-01', submission_status='2')
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.priv}')
        res = self.client.get('/api/v1/licenses/valid/', {'include': 'date_of_birth'})
        self.assertEqual(res.data['results'][0]['date_of_birth'], '1990-05-01')

    def test_lookup_match_minimal_output(self):
        _make_starter(dob='1990-05-01', submission_status='2')
        res = self.client.post(
            '/api/v1/licenses/lookup/',
            {'last_name': 'Mustermann', 'date_of_birth': '1990-05-01'}, format='json',
        )
        self.assertTrue(res.data['valid'])
        match = res.data['matches'][0]
        self.assertEqual(match['license_type'], 'starter')
        # data minimization: no personal fields in the response
        self.assertNotIn('name', match)
        self.assertNotIn('date_of_birth', match)

    def test_lookup_miss(self):
        _make_starter(dob='1990-05-01', submission_status='2')
        res = self.client.post(
            '/api/v1/licenses/lookup/',
            {'last_name': 'Nobody', 'date_of_birth': '1990-05-01'}, format='json',
        )
        self.assertFalse(res.data['valid'])

    def test_lookup_requires_two_identifiers(self):
        res = self.client.post(
            '/api/v1/licenses/lookup/', {'last_name': 'Mustermann'}, format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lookup_get_is_disabled_to_keep_pii_out_of_urls(self):
        res = self.client.get(
            '/api/v1/licenses/lookup/',
            {'last_name': 'Mustermann', 'date_of_birth': '1990-05-01'},
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AuditLogTest(APITestCase):
    def test_denied_request_logged_without_secret_or_query(self):
        _, key = ScopedAPIKey.objects.create_key(name='audit')
        with self.assertLogs('dbfv.audit', level='INFO') as cm:
            # valid key + a search term that must NOT appear in the audit line
            self.client.get(
                '/api/v1/country/', {'search': 'TOPSECRETNAME'},
                HTTP_AUTHORIZATION=f'Api-Key {key}',
            )
            # no key -> 403, logged at WARNING
            self.client.get('/api/v1/country/')
        joined = '\n'.join(cm.output)
        self.assertIn('path=/api/v1/country/', joined)
        self.assertIn('status=403', joined)
        self.assertNotIn('TOPSECRETNAME', joined)  # query/search data never logged
        self.assertNotIn(key.split('.', 1)[1], joined)  # secret never logged
