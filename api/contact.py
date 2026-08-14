"""Public "request an API key" contact form."""
# Django
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

# dbfv
from api.client_ip import client_ip
from api.rate_limit import check_rate_limit
from submission.models import ManagerEmail


class ApiKeyRequestForm(forms.Form):
    name = forms.CharField(label='Name', max_length=100)
    organization = forms.CharField(label='Organisation / Verband', max_length=150)
    email = forms.EmailField(label='E-Mail')
    intended_use = forms.CharField(label='Verwendungszweck', widget=forms.Textarea)
    # Honeypot: real users leave this hidden field empty.
    website = forms.CharField(required=False, widget=forms.HiddenInput, label='')

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Spam erkannt.')
        return ''


def api_key_request(request):
    if request.method == 'POST':
        rate = getattr(settings, 'API_KEY_REQUEST_RATE_LIMIT', '5/hour')
        allowed, retry_after = check_rate_limit(
            'api-key-request', client_ip(request) or 'unknown', rate
        )
        if not allowed:
            response = HttpResponse(
                'Zu viele Anfragen. Bitte später erneut versuchen.', status=429
            )
            response['Retry-After'] = str(retry_after)
            return response
        form = ApiKeyRequestForm(request.POST)
        if form.is_valid():
            recipients = list(ManagerEmail.objects.values_list('email', flat=True))
            if recipients:
                send_mail(
                    subject=f'API-Key-Anfrage: {form.cleaned_data["organization"]}',
                    message=render_to_string('api/api_key_request_email.txt', form.cleaned_data),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@dbfv.com'),
                    recipient_list=recipients,
                    fail_silently=True,
                )
            messages.success(
                request, 'Danke, deine Anfrage wurde übermittelt. Wir melden uns per E-Mail.'
            )
            return redirect('api-key-request')
    else:
        form = ApiKeyRequestForm()
    return render(request, 'api/api_key_request.html', {'form': form})
