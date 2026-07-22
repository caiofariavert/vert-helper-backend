from django.urls import path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="admin:index", permanent=True)),
]
