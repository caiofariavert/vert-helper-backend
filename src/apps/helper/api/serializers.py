from rest_framework import serializers

from apps.helper.models import Action, Application, Ecosystem, Service, System

from .validators import validate_questions


class EcosystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ecosystem
        fields = ["id", "name", "slug", "is_active", "created_at", "updated_at"]


class SystemSerializer(serializers.ModelSerializer):
    ecosystems = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="slug"
    )

    class Meta:
        model = System
        fields = [
            "id", "name", "slug", "description",
            "ecosystems", "is_active", "created_at", "updated_at",
        ]


class ApplicationSerializer(serializers.ModelSerializer):
    system = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = Application
        fields = [
            "id", "name", "slug", "base_url", "environment",
            "system", "is_active", "created_at", "updated_at",
        ]


class ServiceSerializer(serializers.ModelSerializer):
    application = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = Service
        fields = [
            "id", "name", "description", "status",
            "last_checked_at", "last_status_change_at",
            "application", "is_active", "created_at", "updated_at",
        ]


class ActionListSerializer(serializers.ModelSerializer):
    """Serializer usado na listagem de ações (inclui is_recommended anotado)."""

    services = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_recommended = serializers.BooleanField(read_only=True)

    class Meta:
        model = Action
        fields = [
            "id", "slug", "name", "description",
            "services", "status", "is_recommended", "created_at",
        ]

    def get_services(self, obj):
        return list(obj.services.values_list("name", flat=True))

    def get_status(self, obj):
        return "active" if obj.is_active else "inactive"


class ActionDetailSerializer(serializers.ModelSerializer):
    """Serializer usado no detalhe da ação (inclui questions_schema completo)."""

    services = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    questions = serializers.JSONField(source="questions_schema")

    class Meta:
        model = Action
        fields = [
            "id", "slug", "name", "description",
            "services", "status", "questions", "created_at",
        ]

    def get_services(self, obj):
        return list(obj.services.values_list("name", flat=True))

    def get_status(self, obj):
        return "active" if obj.is_active else "inactive"


class ActionExecuteSerializer(serializers.Serializer):
    """
    Valida o payload de execução de uma Action.

    O campo `questions` recebe um dict {question_id: resposta}.
    A validação dinâmica usa o questions_schema da Action para:
      - checar obrigatoriedade de perguntas ativas;
      - validar opções permitidas;
      - ignorar perguntas inativas (parent não satisfeito).

    Após validação, `validated_data["mapped_kwargs"]` contém
    o dict {action_kwarg: valor} pronto para execução.
    """

    questions = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        default=dict,
    )

    def __init__(self, *args, action_schema: list = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._action_schema = action_schema or []

    def validate(self, attrs):
        answers = attrs.get("questions", {})
        mapped_kwargs = validate_questions(self._action_schema, answers)
        attrs["mapped_kwargs"] = mapped_kwargs
        return attrs
