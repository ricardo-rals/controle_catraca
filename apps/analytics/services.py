from django.db.models import Count, QuerySet


def usuarios_frequentes(queryset: QuerySet, limite: int = 20) -> list[dict]:
    """
    Agrupa os registros por identificador_pseudonimizado e retorna os
    usuarios com maior numero de ocorrencias no periodo informado.

    Nunca resolve o identificador para nome/credencial - trabalha
    apenas com o hash ja armazenado, preservando a privacidade.
    """
    resultados = (
        queryset.values("identificador_pseudonimizado")
        .annotate(total=Count("id"))
        .order_by("-total")[:limite]
    )

    return [
        {"identificador": item["identificador_pseudonimizado"], "total": item["total"]}
        for item in resultados
    ]
