import pytest
from rest_framework import serializers

from apps.helper.api.validators import validate_questions
from apps.helper.tests.factories import SIMPLE_QUESTIONS_SCHEMA


class TestValidateQuestions:

    def test_valid_csv_branch(self):
        """CSV selecionado → q2 ativa, q3 inativa → kwargs corretos."""
        answers = {"q1": "CSV", "q2": "Arquivo"}
        kwargs = validate_questions(SIMPLE_QUESTIONS_SCHEMA, answers)
        assert kwargs == {"file_type": "CSV", "csv_source": "Arquivo"}

    def test_valid_json_branch(self):
        """JSON selecionado → q3 ativa, q2 inativa → kwargs corretos."""
        answers = {"q1": "JSON", "q3": "wf-123"}
        kwargs = validate_questions(SIMPLE_QUESTIONS_SCHEMA, answers)
        assert kwargs == {"file_type": "JSON", "workflow_id": "wf-123"}

    def test_missing_required_root_question(self):
        """q1 obrigatória e ausente → erro."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_questions(SIMPLE_QUESTIONS_SCHEMA, {})
        assert "q1" in exc_info.value.detail["questions"]

    def test_missing_required_active_child(self):
        """q1=JSON ativa q3 que é obrigatória → erro se q3 ausente."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_questions(SIMPLE_QUESTIONS_SCHEMA, {"q1": "JSON"})
        assert "q3" in exc_info.value.detail["questions"]

    def test_inactive_child_ignored(self):
        """q2 só é ativa quando q1=CSV; com q1=JSON q2 deve ser ignorada."""
        answers = {"q1": "JSON", "q3": "wf-abc", "q2": "qualquer"}
        kwargs = validate_questions(SIMPLE_QUESTIONS_SCHEMA, answers)
        # csv_source não deve aparecer pois q2 estava inativa
        assert "csv_source" not in kwargs

    def test_invalid_option_for_radio(self):
        """Valor fora das options → erro de validação."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_questions(SIMPLE_QUESTIONS_SCHEMA, {"q1": "XML"})
        assert "q1" in exc_info.value.detail["questions"]

    def test_text_field_accepts_any_value(self):
        """Campo type=text sem options aceita qualquer string."""
        answers = {"q1": "JSON", "q3": "qualquer-valor-livre"}
        kwargs = validate_questions(SIMPLE_QUESTIONS_SCHEMA, answers)
        assert kwargs["workflow_id"] == "qualquer-valor-livre"

    def test_empty_schema_returns_empty_kwargs(self):
        """Schema vazio → kwargs vazios sem erro."""
        assert validate_questions([], {}) == {}
