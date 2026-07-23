from django.urls import include, path

urlpatterns = [
    path("api/helper/v1/", include("apps.helper.api.urls")),
]
