from django.urls import path

from . import views

app_name = "user"

urlpatterns = [
    path("me/", views.MeApiView.as_view(), name="account-me-api"),
]
