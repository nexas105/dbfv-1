# -*- coding: utf-8 -*-

# This file is part of the DBFV submission site
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with the DBFV site.  If not, see <http://www.gnu.org/licenses/>.
# Django
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User as Django_User
from django.core.exceptions import ValidationError
from django.forms import (
    BooleanField,
    DateInput,
    EmailField,
    ModelChoiceField,
    ModelForm,
    MultipleChoiceField, Form, CharField, EmailInput, Textarea,
)
from django.utils.translation import gettext as _

# Third Party
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Column,
    Div,
    HTML,
    Layout,
    Row,
    Submit,
)

# dbfv
from submission.models import (
    BankAccount,
    Gym,
    ManagerEmail,
    State,
    SubmissionGym,
    SubmissionInternational,
    SubmissionJudge,
    SubmissionStarter,
)


def _tune_submission_widgets(form, date_fields):
    """
    Setzt sinnvolle HTML5-Eingabetypen/-Attribute für die Antragsfelder, damit
    Browser (und die Wizard-Schrittprüfung) client-seitig validieren können.
    """
    for name in date_fields:
        form.fields[name].widget = DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
        form.fields[name].input_formats = ['%Y-%m-%d']
    if 'tel_number' in form.fields:
        form.fields['tel_number'].widget.attrs.update({'type': 'tel', 'inputmode': 'tel'})
    if 'zip_code' in form.fields:
        form.fields['zip_code'].widget.attrs.update({'inputmode': 'numeric'})
    if 'height' in form.fields:
        form.fields['height'].widget.attrs.update({'min': 100, 'max': 250, 'inputmode': 'numeric'})
    if 'weight' in form.fields:
        form.fields['weight'].widget.attrs.update({'min': 0, 'step': '0.01', 'inputmode': 'decimal'})


class UserEmailForm(ModelForm):
    email = EmailField(label=_("Email"), required=True)

    def clean_email(self):
        # Email must be unique systemwide
        email = self.cleaned_data["email"]
        if not email:
            return email
        try:
            Django_User.objects.get(email=email)
        except Django_User.DoesNotExist:
            return email
        raise ValidationError(u"Diese Email wird bereits benutzt.")


class RegistrationForm(UserCreationForm, UserEmailForm):
    state = ModelChoiceField(label=_("Bundesverband"), queryset=State.objects.all())

    email = EmailField(label="Email", required=True)

    terms_and_conditions = BooleanField(
        label='Regeln des DBFV e.V.',
        help_text='Hiermit erkläre ich mich mit den Regeln des DBFV e.V. einverstanden',
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Registrieren', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='col-12'),
                Column('email', css_class='col-12'),
                Column('password1', css_class='col-6'),
                Column('password2', css_class='col-6'),
                Column('state', css_class='col-12'),
                Column('terms_and_conditions', css_class='col-12'),
            )
        )

    #captcha = ReCaptchaField(attrs={'theme': 'clean'},
    #                         label=u'Sicherheitscheck',
    #                         help_text=u'Geben Sie bitte die Wörter ein, das dient als '
    #                                   u'Sicherheitsmaßname gegen Spam',)


class SubmissionStarterForm(ModelForm):

    class Meta:
        model = SubmissionStarter
        exclude = ('submission_status', 'pdf_sent')

    CHAMPIONSHIPS = (
        # ('1', u'Deutsche Junioren und Masters am 18.04.2015 in Berlin'),
        # ('2', u'Int. Deutsche Newcomer-Meisterschaft am 25.04.2015 in Fulda/Petersberg'),
        # ('3', u'Deutsche Jugendmeisterschaft am 25.04.2015 in Fulda/Petersberg'),
        # ('4', u'NRW Landesmeisterschaften am 02.05.2015 in Duisburg-Rheinhausen'),
        # ('5', u'NRW Newcomerklasse für Männer am 02.05.2015 in Duisburg-Rheinhausen'),
        # ('6', u'33. Duisburger Stadtmeisterschaft am 02.05.2015 in Duisburg-Rheinhausen'),
        # ('7', u'Int. NRW Meisterschaften am 19.11.2016 in Duisburg-Rheinhausen'),
        # ('8', u'Int. NRW Newcomer-Wertung für Männer am 19.11.2016 in Duisburg-Rheinhausen'),
        ('9', u'NRW Landesmeisterschaft am 06.05.2017 in Duisburg-Rheinhausen'),
        ('10', u'NRW Newcomer-Wertung für Männer am 06.05.2017 in Duisburg-Rheinhausen'),
    )

    gym = ModelChoiceField(queryset=Gym.objects.filter(is_active=True), label='Studio')

    championships = MultipleChoiceField(
        label='Meisterschaften', choices=CHAMPIONSHIPS, required=False
    )

    terms_and_conditions = BooleanField(
        label='Regeln des DBFV e.V.',
        help_text='Hiermit erkläre ich mich mit den Regeln des DBFV e.V. einverstanden',
        required=True
    )

    data_protection = BooleanField(
        label='Datenschutzbestimmungen',
        help_text='Hiermit erkläre ich mich mit den Datenschutzbestimmungen des DBFV e.V. einverstanden',
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        _tune_submission_widgets(self, ['date_of_birth'])

        self.helper = FormHelper()
        self.helper.add_input(
            Submit('submit', 'Abschicken', css_class='btn-success btn-lg wizard-submit')
        )
        self.helper.layout = Layout(
            Div(
                Row(Column('gym', css_class='col-12')),
                css_class='wizard-step wstep-1',
            ),
            Div(
                HTML('<h4 class="wizard-step-title">Persönliche Daten</h4>'),
                Row(
                    Column('first_name', css_class='col-6'),
                    Column('last_name', css_class='col-6'),
                    Column('nationality', css_class='col-12'),
                    Column('date_of_birth', css_class='col-12'),
                    Column('street', css_class='col-6'),
                    Column('house_nr', css_class='col-2'),
                    Column('zip_code', css_class='col-4'),
                    Column('city', css_class='col-8'),
                    Column('tel_number', css_class='col-6'),
                    Column('email', css_class='col-6'),
                ),
                css_class='wizard-step wstep-2',
            ),
            Div(
                HTML('<h4 class="wizard-step-title">Wettkampfdaten</h4>'),
                Row(
                    Column('active_since', css_class='col-6'),
                    Column('category', css_class='col-6'),
                    Column('height', css_class='col-6'),
                    Column('weight', css_class='col-6'),
                ),
                css_class='wizard-step wstep-3',
            ),
            Div(
                HTML('<h4 class="wizard-step-title">Bestätigung</h4>'),
                HTML(
                    '<p>Bitte lesen Sie die '
                    '<a href="#" data-bs-toggle="modal" data-bs-target="#legalModal">'
                    'Wettkampfregeln, Anti-Doping- und Datenschutzbestimmungen</a>. '
                    'Die Zustimmung lässt sich erst ankreuzen, nachdem Sie den Text '
                    'vollständig gelesen (bis ans Ende gescrollt) haben.</p>'
                ),
                Row(
                    Column('terms_and_conditions', css_class='col-12'),
                    Column('data_protection', css_class='col-12'),
                ),
                css_class='wizard-step wstep-4',
            ),
        )


class SubmissionInternationalForm(ModelForm):

    gym = ModelChoiceField(queryset=Gym.objects.filter(is_active=True), label='Studio')

    terms_and_conditions = BooleanField(
        label='Regeln des DBFV e.V.',
        help_text='Hiermit erkläre ich mich mit den Regeln des DBFV e.V. einverstanden',
        required=True
    )

    class Meta:
        model = SubmissionInternational
        exclude = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        _tune_submission_widgets(self, ['date_of_birth', 'championship_date'])

        self.helper = FormHelper()
        self.helper.add_input(
            Submit('submit', 'Speichern', css_class='btn-success btn-lg wizard-submit')
        )
        self.helper.layout = Layout(
            Div(
                Row(Column('gym', css_class='col-12')),
                css_class='wizard-step wstep-1',
            ),
            Div(
                HTML('<h4 class="wizard-step-title">Persönliche Daten</h4>'),
                Row(
                    Column('first_name', css_class='col-6'),
                    Column('last_name', css_class='col-6'),
                    Column('date_of_birth', css_class='col-6'),
                    Column('nationality', css_class='col-6'),
                    Column('street', css_class='col-8'),
                    Column('zip_code', css_class='col-4'),
                    Column('city', css_class='col-6'),
                    Column('tel_number', css_class='col-6'),
                    Column('email', css_class='col-12'),
                ),
                css_class='wizard-step wstep-2',
            ),
            Div(
                HTML('<h4 class="wizard-step-title">Wettkampfdaten</h4>'),
                Row(
                    Column('height', css_class='col-6'),
                    Column('weight', css_class='col-6'),
                    Column('category', css_class='col-12'),
                    Column('championship', css_class='col-6'),
                    Column('championship_date', css_class='col-6'),
                    Column('best_placement', css_class='col-12'),
                ),
                css_class='wizard-step wstep-3',
            ),
            Div(
                HTML('<h4 class="wizard-step-title">Bestätigung</h4>'),
                Row(Column('terms_and_conditions', css_class='col-12')),
                css_class='wizard-step wstep-4',
            ),
        )


class SubmissionInternationalFormBV(ModelForm):

    class Meta:
        model = SubmissionInternational
        fields = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(Row(Column('submission_status', css_class='col-12'), ))


class SubmissionStarterFormBV(ModelForm):

    class Meta:
        model = SubmissionStarter
        fields = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(Column('submission_status', css_class='col-12'), css_class='form-row')
        )


class SubmissionGymForm(ModelForm):

    class Meta:
        model = SubmissionGym
        exclude = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('state', css_class='col-12'),
                Column('name', css_class='col-4'),
                Column('owner', css_class='col-4'),
                Column('founded', css_class='col-4'),
                Column('street', css_class='col-4'),
                Column('zip_code', css_class='col-2 '),
                Column('city', css_class='col-6 '),
                Column('email', css_class='col-6 '),
                Column('tel_number', css_class='col-6'),
            )
        )


class SubmissionGymFormBV(ModelForm):

    class Meta:
        model = SubmissionGym
        fields = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('submission_status', css_class='col-12')
            )
        )


class SubmissionJudgeForm(ModelForm):
    data_protection = BooleanField(
        label='Datenschutzbestimmungen',
        help_text='Hiermit erkläre ich mich mit den Datenschutzbestimmungen des DBFV e.V. einverstanden',
        required=True
    )

    class Meta:
        model = SubmissionJudge
        exclude = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-6'),
                Column('last_name', css_class='col-6'),
                Column('street', css_class='col-4 '),
                Column('zip_code', css_class='col-2 '),
                Column('city', css_class='col-6 '),
                Column('tel_number', css_class='col-12 '),
                Column('email', css_class='col-12 '),
                Column('state', css_class='col-12 '),
                Column('data_protection', css_class='col-12'),
            )
        )


class SubmissionJudgeFormBV(ModelForm):

    class Meta:
        model = SubmissionJudge
        fields = ('submission_status', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(Row(Column('submission_status', css_class='col-12'), ))


class GymForm(ModelForm):
    """
    Gym form
    """

    class Meta:
        model = Gym
        fields = [
            'name',
            'email',
            'state',
            'owner',
            'zip_code',
            'city',
            'street',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-12'),
                Column('email', css_class='col-6'),
                Column('state', css_class='col-6'),
                Column('owner', css_class='col-12'),
                Column('zip_code', css_class='col-3'),
                Column('city', css_class='col-5'),
                Column('street', css_class='col-4'),
                Column('is_active', css_class='col-6'),
            )
        )


class StateForm(ModelForm):
    """
    Form for a state
    """

    class Meta:
        model = State
        fields = ['name', 'short_name', 'email', 'bank_account']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-6'),
                Column('short_name', css_class='col-6'),
                Column('email', css_class='col-12'),
                Column('bank_account', css_class='col-12'),
            )
        )


class BankAccountForm(ModelForm):
    """
    Form for a bank account
    """

    class Meta:
        model = BankAccount
        fields = ['owner_name', 'iban', 'bic', 'bank_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('bank_name', css_class='col-12'),
                Column('owner_name', css_class='col-12'),
                Column('iban', css_class='col-6'),
                Column('bic', css_class='col-6'),
            )
        )


class ManagerEmailForm(ModelForm):
    """
    Form for a bank account
    """

    class Meta:
        model = ManagerEmail
        fields = [
            'email',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern', css_class='btn-success'))
        self.helper.layout = Layout(Row(Column('email', css_class='col-12'), css_class='form-row'))


class DbfvAuthenticationForm(AuthenticationForm):
    """
    Form used for logging in to the DBFV application
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Anmelden', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='col-6'),
                Column('password', css_class='col-6'),
            )
        )


class DbfvPasswordResetForm(PasswordResetForm):
    """
    Form used to reset a password
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Abschicken', css_class='btn-success'))
        self.helper.layout = Layout(Row(Column('email', css_class='col-12'), css_class='form-row'))


class DbfvSetPasswordForm(SetPasswordForm):
    """
    Form used to reset a password
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Abschicken', css_class='btn-success'))
        self.helper.layout = Layout(
            Row(
                Column('new_password1', css_class='col-12'),
                Column('new_password2', css_class='col-12'),
            )
        )


class MassenbewilligungForm(Form):
    bewilligungen = CharField(
        label="IDs der zu bewilligenden Anträge",
        help_text="Eine ID pro Zeile",
        max_length=254,
        widget=Textarea(attrs={'rows': '10'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Abschicken', css_class='btn-success'))
        self.helper.add_input(Submit('check', 'Prüfen', css_class='btn-success'))

        self.helper.layout = Layout(
            Row(
                Column('bewilligungen', css_class='col-12'),
            )
        )