import django_filters

from apps.helper.models import Action, Application, Ecosystem, Service, System


class EcosystemFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Ecosystem
        fields = ["search"]


class SystemFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    ecosystem = django_filters.CharFilter(
        field_name="ecosystems__slug", lookup_expr="exact"
    )

    class Meta:
        model = System
        fields = ["search", "ecosystem"]


class ApplicationFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    system = django_filters.CharFilter(field_name="system__slug", lookup_expr="exact")
    ecosystem = django_filters.CharFilter(
        field_name="system__ecosystems__slug", lookup_expr="exact"
    )

    class Meta:
        model = Application
        fields = ["search", "system", "ecosystem"]


class ServiceFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    application = django_filters.CharFilter(
        field_name="application__slug", lookup_expr="exact"
    )
    system = django_filters.CharFilter(
        field_name="application__system__slug", lookup_expr="exact"
    )

    class Meta:
        model = Service
        fields = ["search", "application", "system"]


class ActionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter")
    service = django_filters.CharFilter(
        field_name="services__name", lookup_expr="iexact"
    )
    application = django_filters.CharFilter(
        field_name="application__slug", lookup_expr="exact"
    )

    class Meta:
        model = Action
        fields = ["search", "service", "application"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(name__icontains=value) | queryset.filter(
            description__icontains=value
        )
