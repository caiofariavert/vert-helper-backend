"""
Validação dinâmica do schema de perguntas de uma Action.

Regras:
- Uma pergunta é "ativa" se não possui parent_question ou se a resposta ao
  parent_question for igual ao parent_value exato.
- Perguntas inativas são ignoradas (não obrigatórias, não mapeadas).
- Perguntas ativas com is_required=True devem ter resposta presente e não vazia.
- Perguntas com options != null devem ter resposta dentro das opções válidas.
- O retorno de validate_questions() é o dict de kwargs mapeado por action_kwarg.
"""

from rest_framework import serializers


def _is_active(question: dict, answers: dict) -> bool:
    """Retorna True se a pergunta deve ser considerada na validação."""
    parent_id = question.get("parent_question")
    if parent_id is None:
        return True
    return answers.get(parent_id) == question.get("parent_value")


def validate_questions(schema: list, answers: dict) -> dict:
    """
    Valida as respostas contra o schema e retorna os kwargs mapeados.

    :param schema: lista de perguntas conforme questions_schema da Action.
    :param answers: dict {question_id: valor_respondido} enviado pelo frontend.
    :returns: dict {action_kwarg: valor} pronto para passar à execução.
    :raises serializers.ValidationError: se alguma regra for violada.
    """
    errors = {}
    kwargs = {}

    for question in schema:
        qid = question["id"]
        kwarg = question["action_kwarg"]
        is_required = question.get("is_required", False)
        options = question.get("options")

        if not _is_active(question, answers):
            continue

        value = answers.get(qid)

        if is_required and (value is None or value == ""):
            errors[qid] = f"A pergunta '{question.get('label', qid)}' é obrigatória."
            continue

        if value is not None and options is not None and value not in options:
            errors[qid] = (
                f"Resposta inválida para '{question.get('label', qid)}'. "
                f"Valores aceitos: {options}."
            )
            continue

        if value is not None:
            kwargs[kwarg] = value

    if errors:
        raise serializers.ValidationError({"questions": errors})

    return kwargs
