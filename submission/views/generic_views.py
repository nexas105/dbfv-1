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
# Standard Library
import csv
import datetime

# Django
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.urls import (
    reverse,
    reverse_lazy,
)
from django.views import generic
from django.views.generic.base import (
    TemplateResponseMixin,
    View,
)
from django.views.generic.edit import ModelFormMixin

# dbfv
from submission.models import (
    USER_TYPE_BUNDESVERBAND,
    user_type,
)


def csv_safe(value):
    """
    Neutralize spreadsheet formula injection.

    Cells starting with =, +, -, @ or a leading tab/CR can be interpreted as
    a formula by spreadsheet apps; prefix them with an apostrophe so they are
    read as text.
    """
    text = '' if value is None else str(value)
    if text[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


class DbfvViewMixin(TemplateResponseMixin):
    permission_required = ''
    login_required = False

    def dispatch(self, request, *args, **kwargs):
        """
        Check for necessary permissions
        """
        if self.login_required or self.permission_required:
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse('login') + '?next=%s' % request.path)

            if self.permission_required and \
                    not request.user.has_perm(self.permission_required):
                return HttpResponseForbidden()

        return super().dispatch(request, *args, **kwargs)


class DbfvFormMixin(DbfvViewMixin, ModelFormMixin):

    page_title = ''
    template_name = 'form.html'

    def get_context_data(self, **kwargs):
        """
        Set the context data
        """

        context = super().get_context_data(**kwargs)
        context['form_action'] = self.request.get_full_path()
        context['title'] = self.page_title

        return context


#
# Submissions
#


class BaseSubmissionCreateView(DbfvFormMixin, generic.CreateView):
    """
    Creates a new submissions
    """

    extra_data = []

    def form_valid(self, form):
        """
        Manually set the user when saving the form
        """
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """
        Redirect to bank account page and send appropriate emails
        """
        self.object.send_emails(self.extra_data)
        self.request.session['bank-account'] = self.object.get_bank_account()
        self.request.session['submission-fee'] = self.model.FEE
        self.request.session['designated-use'] = self.object.get_bank_designated_use()
        return reverse_lazy('bank-account-view')

    def get_context_data(self, **kwargs):
        """
        Pass a list of all states
        """
        context = super().get_context_data(**kwargs)
        context['fee'] = self.model.FEE
        return context

    def get_initial(self):
        """
        Fill in some data
        """
        return {'email': self.request.user.email}


class BaseSubmissionDeleteView(DbfvViewMixin, generic.DeleteView):
    """
    Deletes a submission
    """

    template_name = 'delete.html'

    def dispatch(self, request, *args, **kwargs):
        # Require the delete permission for the concrete model, not a fixed one.
        self.permission_required = f'submission.delete_{self.model._meta.model_name}'
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Pass the title to the context
        """
        context = super(BaseSubmissionDeleteView, self).get_context_data(**kwargs)
        context['title'] = u'Antrag {0} löschen?'.format(self.object.id)
        return context


class BaseSubmissionListView(DbfvViewMixin, generic.ListView):
    # context_object_name = "submission_list"
    login_required = True


class BaseSubmissionUpdateView(DbfvFormMixin, generic.UpdateView):
    """
    Updates an existing submission

    The owner user can update his own submission while it is still in the
    pending state. Once it has been accepted, only the BV can edit it.
    """

    login_required = True
    page_title = 'Antrag bearbeiten'

    def dispatch(self, request, *args, **kwargs):
        """
        Check for necessary permissions
        """
        submission = self.get_object()
        change_perm = f'submission.change_{self.model._meta.model_name}'
        if not request.user.has_perm(change_perm) \
            and (submission.submission_status != submission.SUBMISSION_STATUS_EINGEGANGEN
                 or submission.user != request.user):
            return HttpResponseForbidden(u'Sie dürfen dieses Objekt nicht editieren!')

        return super(BaseSubmissionUpdateView, self).dispatch(request, *args, **kwargs)


#
# CSV Export
#
class BaseCsvExportView(View):
    """
    Base view to implement the common CSV export logic
    """
    http_method_names = ['get']
    update_submission_flag = True
    model = None

    def dispatch(self, request, *args, **kwargs):
        """
        Check for necessary permissions
        """
        if not request.user.has_perm(f'submission.change_{self.model._meta.model_name}'):
            return HttpResponseForbidden()

        return super(BaseCsvExportView, self).dispatch(request, *args, **kwargs)

    def get_submission_list(self):
        """
        Return a list of submissions to export.

        Default: all non-exported submissions
        """
        submission_status = self.model.SUBMISSION_STATUS_BEWILLIGT
        submissions = self.model.objects.filter(mail_merge=False) \
                                        .filter(submission_status=submission_status) \
                                        .select_related()

        return submissions

    def export_submission_mailmerge(self, submission_list):
        """
        Generates a list with starter submission fields to be used in mail merge

        :param submission_list: A list of Submissions
        """
        result = []
        for submission in submission_list:
            result.append(submission.get_mailmerge_row())
        return result

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response, delimiter='\t')
        today = datetime.date.today()
        submissions = self.get_submission_list()

        # Write the CSV file (cells neutralized against formula injection)
        writer.writerow([csv_safe(cell) for cell in self.model.MAILMERGE_HEADER])
        for line in self.export_submission_mailmerge(submissions):
            writer.writerow([csv_safe(cell) for cell in line])

        # If necessary, update the submission flag
        if self.update_submission_flag:
            submissions.update(mail_merge=True)

        license_type = self.model.get_license_type()
        filename = 'attachment; filename=Export-{0}-{1}-{2}-{3}.csv'.format(
            license_type, today.year, today.month, today.day
        )
        response['Content-Disposition'] = filename
        response['Content-Length'] = len(response.content)
        return response


def get_overview_context(model_class, queryset, user, **kwargs):
    """
    Pass a list of all available dates
    """
    context = {}

    # Count how many submissions were exported for each month
    month_list = []
    for date_obj in queryset.dates('creation_date', 'month'):
        tmp_count = model_class.objects.filter(pdf_sent=True)\
                                       .filter(creation_date__month=date_obj.month)\
                                       .filter(creation_date__year=date_obj.year)

        month_list.append({'date': date_obj, 'export_count': tmp_count.count()})
    context['submission_list'] = queryset
    context['month_list'] = month_list
    context['current_year'] = datetime.date.today().year
    context['current_month'] = datetime.date.today().month
    context['show_closed'] = True
    # context['show_closed'] = True if user_type(user) == USER_TYPE_BUNDESVERBAND else True
    context['mailmerge_count'] = model_class.objects.filter(mail_merge=False) \
        .filter(submission_status=model_class.SUBMISSION_STATUS_BEWILLIGT) \
        .count()
    return context
