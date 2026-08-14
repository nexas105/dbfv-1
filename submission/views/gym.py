# -*- coding: utf-8 -*-
import csv
import datetime

from django.http import HttpResponseForbidden, HttpResponse
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
from django.urls import reverse_lazy
from django.views import generic

# dbfv
from submission.forms import GymForm
from submission.models import (
    Gym,
    State,
)
from submission.views.generic_views import (
    DbfvFormMixin,
    DbfvViewMixin,
    csv_safe,
)


class GymListView(DbfvViewMixin, generic.ListView):
    """
    Shows a list with all gyms
    """

    context_object_name = "gym_list"
    model = Gym
    template_name = 'gym/list.html'
    permission_required = 'submission.change_gym'

    def get_queryset(self):
        """
        Filter by state
        """
        return Gym.objects.filter(state=self.kwargs['state_pk'])

    def get_context_data(self, **kwargs):
        """
        Pass the state to the context
        """
        context = super(GymListView, self).get_context_data(**kwargs)
        context['state'] = State.objects.get(pk=self.kwargs['state_pk'])
        return context


class GymDetailView(DbfvViewMixin, generic.DetailView):
    """
    Detail view of a gym
    """

    model = Gym
    template_name = 'gym/view.html'
    permission_required = 'submission.change_gym'


class GymCreateView(DbfvFormMixin, generic.CreateView):
    """
    Creates a new gym
    """

    model = Gym
    permission_required = 'submission.add_gym'
    page_title = 'Studio hinzufügen'
    form_class = GymForm


class GymUpdateView(DbfvFormMixin, generic.UpdateView):
    """
    Edits an existing Gym
    """

    model = Gym
    permission_required = 'submission.change_gym'
    page_title = 'Studio bearbeiten'
    form_class = GymForm


class GymDeleteView(DbfvFormMixin, generic.DeleteView):
    """
    Deletes a gym
    """

    model = Gym
    success_url = reverse_lazy('gym-list')
    permission_required = 'submission.delete_gym'
    template_name = 'delete.html'

    def get_context_data(self, **kwargs):
        """
        Pass the title to the context
        """
        context = super().get_context_data(**kwargs)
        context['title'] = u'Studio {0} löschen?'.format(self.object.name)
        context['delete_message'] = u'Das wird auch alle Anträge zu diesem Studio entfernen.'
        return context


def export_csv(request):
    """
    Search for a submission, return the result as a JSON list
    """
    if not request.user.has_perm('submission.change_submissionstarter'):
        return HttpResponseForbidden()

    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Bundesland', 'Name', 'Email'])

    today = datetime.date.today()
    for gym in Gym.objects.filter(is_active=True):
        writer.writerow([csv_safe(gym.state.short_name), csv_safe(gym.name), csv_safe(gym.email)])

    filename = f'attachment; filename=Email-export-aktive-Studios-{today}.csv'
    response['Content-Disposition'] = filename
    response['Content-Length'] = len(response.content)
    return response
