# For testing, it is very often useful to become another user. This
# middleware makes it possible to add ?impersonate=username to any
# URL, and then the page will be shown as that user.

from django.contrib.auth.models import User


class ImpersonateMiddleware(object):
    def process_request(self, request):
        if request.user.is_superuser:
            impersonate = request.GET.get("__impersonate")
            if impersonate:
                request.session['impersonate_username'] = impersonate
            elif "__unimpersonate" in request.GET:
                del request.session['impersonate_username']

            if 'impersonate_username' in request.session:
                user = User.objects.get(
                    username=request.session['impersonate_username'])
                request.user = user
