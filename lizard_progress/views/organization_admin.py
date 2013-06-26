from lizard_ui.views import UiView

from lizard_progress.views.views import KickOutMixin


class OrganizationAdminView(KickOutMixin, UiView):
    template_name = "lizard_progress/organization_admin.html"
