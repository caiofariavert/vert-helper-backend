from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django_cas_ng import views as cas_views
from rest_framework_simplejwt.tokens import RefreshToken


class APILoginView(cas_views.LoginView):
    def successful_login(self, request: HttpRequest, next_page: str) -> HttpResponse:
        """
        This method is called on successful login. Override this method for
        custom post-auth actions (i.e, to add a cookie with a token).


        :param request:
        :param next_page:
        :return:
        """
        user = request.user

        refresh = RefreshToken.for_user(request.user)

        # create jwt token
        jwt_token = refresh.access_token
        refresh_token = str(refresh)
        update_last_login(None, user)

        if "/admin" in next_page:
            return HttpResponseRedirect(next_page)

        bracket = "" if settings.FRONTEND_AUTH_REDIRECT[-1] == "/" else "/"

        new_next_page = next_page
        new_next_page = (
            f"{settings.FRONTEND_AUTH_REDIRECT}{bracket}{jwt_token}/{refresh_token}/"
        )

        return HttpResponseRedirect(new_next_page)
