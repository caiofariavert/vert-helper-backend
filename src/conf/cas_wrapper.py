from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django_cas_ng import views as cas_views
from rest_framework_simplejwt.tokens import RefreshToken


class APILoginView(cas_views.LoginView):
    """
    CAS login view que emite JWT ao usuário autenticado.

    Fluxo:
    1. Usuário é redirecionado para o CAS server.
    2. CAS autentica e retorna ticket para este backend.
    3. Backend valida o ticket, cria/atualiza o usuário local e emite JWT.
    4. Usuário é redirecionado para FRONTEND_AUTH_REDIRECT com os tokens.

    Importante:
    - O JWT é emitido para qualquer usuário autenticado via CAS.
    - O acesso às rotas funcionais do Helper exige is_superuser=True.
    - A promoção de usuário a superusuário deve ser feita manualmente via Django Admin.
    """
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
