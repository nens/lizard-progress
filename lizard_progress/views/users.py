"""User management views."""

from django.contrib.auth import models as authmodels
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.http import HttpResponse

from lizard_progress import forms
from lizard_progress import models
from lizard_progress.views.views import ProjectsView

import logging
logger = logging.getLogger(__name__)


class UserManagementView(ProjectsView):
    template_name = "lizard_progress/usermanagement.html"

    def dispatch(self, *args, **kwargs):
        """This page is only accessible for ROLE_ADMIN users."""

        # Call super first so things like self.profile are set
        page = super(UserManagementView, self).dispatch(*args, **kwargs)

        if (not hasattr(self, 'profile') or
            not self.profile.has_role(models.UserRole.ROLE_ADMIN)):
            raise PermissionDenied()

        return page

    def users(self):
        """Return list of userprofiles of users in this organization,
        ordered by username."""
        return models.UserProfile.objects.filter(
            organization=self.organization,
            user__is_active=True).order_by('user__username')


class SingleUserManagementView(ProjectsView):
    template_name = "lizard_progress/singleuser.html"

    def dispatch(self, request, *args, **kwargs):
        """This page is only accessible for ROLE_ADMIN users, or the
        user himself."""

        userid = kwargs.pop('user_id')
        self.edited_user = authmodels.User.objects.get(pk=userid)

        editing_user = models.UserProfile.get_by_user(request.user)
        editing_user_is_admin = editing_user.has_role(
            models.UserRole.ROLE_ADMIN)

        if self.edited_user != request.user:
            organization = models.Organization.get_by_user(self.edited_user)
            if not (organization.contains_user(request.user) and
                    editing_user_is_admin):
                raise PermissionDenied()

        if request.method == 'POST':
            self.form = forms.SingleUserForm(self.edited_user, request.POST)
        else:
            self.form = forms.SingleUserForm(self.edited_user, initial={
                'username': self.edited_user.username,
                'first_name': self.edited_user.first_name,
                'last_name': self.edited_user.last_name,
                'email': self.edited_user.email
            })

        if editing_user_is_admin:
            self.form.add_role_fields(
                editing_self=(self.edited_user == request.user))

        return super(SingleUserManagementView, self).dispatch(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        logger.debug(self.form.cleaned_data)

        self.form.update_user()

        return HttpResponseRedirect(reverse(
            "lizard_progress_single_user_management", kwargs={
                'user_id': self.edited_user.id}))

    def delete(self, request, *args, **kwargs):
        """Delete this user."""
        # Can't delete yourself.
        if self.edited_user != request.user:
            self.edited_user.is_active = False
            self.edited_user.save()
        return HttpResponse()


class NewUserManagementView(ProjectsView):
    template_name = "lizard_progress/singleuser.html"

    def dispatch(self, request, *args, **kwargs):
        """This page is only accessible for ROLE_ADMIN users."""

        editing_user = models.UserProfile.get_by_user(request.user)
        if not editing_user.has_role(models.UserRole.ROLE_ADMIN):
            raise PermissionDenied()

        show_admin_role = editing_user.organization.is_project_owner

        if request.method == 'POST':
            self.form = forms.SingleUserForm(None, request.POST)
        else:
            self.form = forms.SingleUserForm(None)

        self.form.add_role_fields(
            editing_self=False, show_admin_role=show_admin_role)

        return super(NewUserManagementView, self).dispatch(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.form.is_valid():
            return self.get(request, *args, **kwargs)

        newuser = self.form.update_user(organization=self.organization)

        return HttpResponseRedirect(reverse(
            "lizard_progress_single_user_management", kwargs={
                'user_id': newuser.id}))
