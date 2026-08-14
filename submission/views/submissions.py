# -*- coding: utf-8 -*-
import csv
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
# Standard Library
import datetime
import json

# Django
from django.db.models import Q
from django.http.response import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.views.decorators.http import require_POST

# dbfv
from submission.forms import (
    SubmissionStarterForm,
    SubmissionStarterFormBV, MassenbewilligungForm,
)
from submission.helpers import build_starter_pdf, build_judge_pdf
from submission.models import (
    USER_TYPE_BUNDESVERBAND,
    USER_TYPE_USER,
    State,
    SubmissionStarter,
    user_type, SubmissionJudge,
)
from submission.views.generic_views import (
    BaseCsvExportView,
    BaseSubmissionCreateView,
    BaseSubmissionDeleteView,
    BaseSubmissionListView,
    BaseSubmissionUpdateView,
    DbfvFormMixin,
    csv_safe,
    DbfvViewMixin,
    get_overview_context,
)


class SubmissionListView(BaseSubmissionListView):
    """
    Shows a list with all submissions
    """

    model = SubmissionStarter
    template_name = 'submission/starter/list.html'

    def get_queryset(self):
        """
        Show the submissions from the last two years
        """

        diff = datetime.datetime.now() - datetime.timedelta(weeks=100)
        return SubmissionStarter.objects.none()
        # return SubmissionStarter.objects.filter(creation_date__gt=diff)

    def get_context_data(self, **kwargs):
        """
        Pass a list of all available dates
        """
        context = super().get_context_data(**kwargs)

        diff = datetime.datetime.now() - datetime.timedelta(weeks=100)
        queryset = SubmissionStarter.objects.filter(creation_date__gt=diff).order_by(
            'gym__state',
            'creation_date',
        )

        # queryset = SubmissionStarter.objects.all().order_by('gym__state', 'creation_date')
        if user_type(self.request.user) == USER_TYPE_USER:
            queryset = queryset.filter(user=self.request.user)

        context.update(get_overview_context(self.model, queryset, self.request.user))
        return context


class SubmissionListMonthView(
    SubmissionListView,
    generic.dates.MonthMixin,
    generic.dates.YearMixin,
):
    permission_required = 'submission.change_submissionstarter'

    def get_queryset(self):
        """
        Change the queryset depending on the user's rights. The rules are the
        following:
            * A BV user sees all submissions
            * A regular user sees it's own submissions
        """

        queryset = SubmissionStarter.objects.filter(creation_date__month=self.get_month()) \
            .filter(creation_date__year=self.get_year()) \
            .order_by('gym__state', 'creation_date')
        if user_type(self.request.user) == USER_TYPE_BUNDESVERBAND:
            return queryset
        elif user_type(self.request.user) == USER_TYPE_USER:
            return queryset.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        """
        Pass a list of all available dates
        """

        context = super().get_context_data(**kwargs)

        # Count how many submissions were exported for each month
        month_list = []
        for date_obj in SubmissionStarter.objects.all().dates('creation_date', 'month'):
            tmp_count = SubmissionStarter.objects.filter(pdf_sent=True) \
                .filter(creation_date__month=date_obj.month) \
                .filter(creation_date__year=date_obj.year)
            month_list.append({'date': date_obj, 'export_count': tmp_count.count()})
        context['submission_list'] = self.get_queryset()
        context['month_list'] = month_list
        context['current_year'] = datetime.date.today().year
        context['current_month'] = datetime.date.today().month
        context['show_closed'] = True
        return context


class SubmissionDetailView(DbfvViewMixin, generic.detail.DetailView):
    """
    Show the detail view of a submission
    """
    login_required = True
    model = SubmissionStarter
    template_name = 'submission/starter/view.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Check for necessary permissions
        """
        submission = self.get_object()
        if not request.user.has_perm('submission.delete_submissionstarter') \
                and submission.user != request.user:
            return HttpResponseForbidden()

        # Save submission data to the session
        self.request.session['bank-account'] = submission.get_bank_account()
        self.request.session['submission-fee'] = SubmissionStarter.FEE
        self.request.session['designated-use'] = submission.get_bank_designated_use()
        return super(SubmissionDetailView, self).dispatch(request, *args, **kwargs)


class SubmissionCreateView(BaseSubmissionCreateView):
    """
    Creates a new submission
    """

    model = SubmissionStarter
    form_class = SubmissionStarterForm
    permission_required = 'submission.add_submissionstarter'
    template_name = 'submission/starter/create.html'

    def form_valid(self, form):
        """
        Set extra data needed for the email
        """

        def get_option(option):
            for i in form.fields['championships'].choices:
                if i[0] == option:
                    return i[1]

        self.extra_data = {
            'championships': [get_option(i) for i in form.cleaned_data['championships']]
        }
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """
        Pass a list of all states
        """
        context = super().get_context_data(**kwargs)
        context['states_list'] = State.objects.all()
        return context


class SubmissionDeleteView(BaseSubmissionDeleteView):
    """
    Deletes a submission
    """
    model = SubmissionStarter
    success_url = reverse_lazy('submission-list')


class SubmissionUpdateView(BaseSubmissionUpdateView):
    """
    Updates an existing submission
    """
    model = SubmissionStarter
    form_class = SubmissionStarterForm


class SubmissionUpdateStatusView(DbfvFormMixin, generic.UpdateView):
    """
    Updates an existing submissions
    """

    model = SubmissionStarter
    form_class = SubmissionStarterFormBV
    success_url = reverse_lazy('submission-list')
    permission_required = 'submission.change_submissionstarter'


class SubmissionCsvExportView(BaseCsvExportView):
    """
    Exports all non-exported submissions to use for mail merge
    """
    model = SubmissionStarter


class SubmissionCsvIndividualExportView(BaseCsvExportView):
    """
    Exports an individual submission to use for mail merge
    """

    model = SubmissionStarter
    update_submission_flag = False

    def get_submission_list(self):
        """
        Return the current submission to export.
        """
        return self.model.objects.filter(pk=self.kwargs['pk'])


def search(request):
    """
    Search for a submission, return the result as a JSON list
    """
    if not request.user.has_perm('submission.change_submissionstarter'):
        return HttpResponseForbidden()

    # Perform the search
    q = request.GET.get('q', '')

    if q:
        submissions = (
            SubmissionStarter.objects.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(gym__name__icontains=q)
            ).distinct()
        )
        results = []
        for submission in submissions[:30]:
            results.append(submission.get_search_json())
        data = json.dumps(results)

    else:
        data = []

    return HttpResponse(data, content_type='application/json')


def export_csv(request):
    """
    Search for a submission, return the result as a JSON list
    """
    if not request.user.has_perm('submission.change_submissionstarter'):
        return HttpResponseForbidden()

    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Name', 'Email'])

    today = datetime.date.today()
    for submission in SubmissionStarter.objects.filter(
            creation_date__year=today.year,
            submission_status=SubmissionStarter.SUBMISSION_STATUS_BEWILLIGT
    ):
        writer.writerow([csv_safe(submission.get_name), csv_safe(submission.email)])

    filename = f'attachment; filename=Email-export-Starterlizenzen-{today.year}-{today}.csv'
    response['Content-Disposition'] = filename
    response['Content-Length'] = len(response.content)
    return response


def massenbewilligung(request):
    """
    Search for a submission, return the result as a JSON list
    """
    if not request.user.has_perm('submission.change_submissionstarter'):
        return HttpResponseForbidden()

    # Perform the search
    form = MassenbewilligungForm(request.POST or None)

    context = {'form': form, 'step': 1}

    # if POST, then process data
    if request.method == 'POST':
        if form.is_valid():
            # Get the data
            data = form.cleaned_data
            ids = data['bewilligungen'].split("\n")
            starter_ok = []
            starter_notok = []

            for id in ids:
                pk = id.strip()
                if pk:
                    try:
                        submission = SubmissionStarter.objects.get(id=pk)
                        starter_ok.append(submission)
                    except (SubmissionStarter.DoesNotExist, ValueError):
                        starter_notok.append(id)

            if context['step'] == 1:
                context['starter_ok'] = starter_ok
                context['starter_notok'] = starter_notok
                context['step'] = 2

            if context['step'] == 2 and request.POST.get('submit'):
                for antrag in starter_ok:
                    antrag.submission_status = SubmissionStarter.SUBMISSION_STATUS_BEWILLIGT
                    antrag.save()
                return HttpResponseRedirect(reverse('submission-list'))

    return render(request, 'submission/starter/massenbewilligung.html', context)


def pdf(request, pk):
    """
    Search for a submission, return the result as a JSON list
    """

    # Get the submission
    submission = get_object_or_404(SubmissionStarter, pk=pk)
    if not request.user.has_perm('submission.delete_submissionstarter') \
            and submission.user != request.user:
        return HttpResponseForbidden()

    response = HttpResponse(content_type='application/pdf')
    build_starter_pdf(request, submission, response)
    response['Content-Length'] = len(response.content)

    return response


def judge_pdf(request, pk):
    """
    Search for a submission, return the result as a JSON list
    """

    # Get the submission
    submission = get_object_or_404(SubmissionJudge, pk=pk)
    if not request.user.has_perm('submission.delete_submissionjudge') \
            and submission.user != request.user:
        return HttpResponseForbidden()

    response = HttpResponse(content_type='application/pdf')
    build_judge_pdf(request, submission, response)
    response['Content-Length'] = len(response.content)

    return response


@require_POST
def send_pdf(request, pk):
    """
    Re-sends the PDF to the given submission
    """
    if not request.user.has_perm('submission.change_submissionstarter'):
        return HttpResponseForbidden()

    submission = get_object_or_404(SubmissionStarter, pk=pk)
    submission.send_pdf_email()

    return HttpResponseRedirect(submission.get_absolute_url())


@require_POST
def send_judge_pdf(request, pk):
    """
    Re-sends the PDF to the given submission
    """
    if not request.user.has_perm('submission.change_submissionjudge'):
        return HttpResponseForbidden()

    submission = get_object_or_404(SubmissionJudge, pk=pk)
    submission.send_pdf_email()

    return HttpResponseRedirect(submission.get_absolute_url())
