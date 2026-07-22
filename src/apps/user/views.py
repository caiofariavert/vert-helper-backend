from django.conf import settings
from django.contrib.auth import forms as forms_auth
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse_lazy

from .forms import ValidationConfirmNewPassword


class AccountPasswordResetView(PasswordResetView):
    template_name = "user/password_reset.html"
    email_template_name = "user/mail/password_forget.html"
    html_email_template_name = "user/mail/password_forget.html"
    subject_template_name = "user/mail/passsword_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    from_email = settings.EMAIL_FROM
    form_class = forms_auth.PasswordResetForm


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "user/password_forget_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "user/password_resend.html"
    token_generator = default_token_generator
    success_url = reverse_lazy("accounts:password_reset_complete")
    reset_url_token = "set-password"
    form_class = ValidationConfirmNewPassword


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "user/password_forget_complete.html"
