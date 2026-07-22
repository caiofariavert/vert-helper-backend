from django.urls import include, path

from .views import (
    AccountPasswordResetCompleteView,
    AccountPasswordResetConfirmView,
    AccountPasswordResetDoneView,
    AccountPasswordResetView,
)

app_name = "accounts"

urlpatterns = [
    path("password_reset/", AccountPasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        AccountPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        AccountPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        AccountPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("api/user/", include("apps.user.api.urls")),
]
