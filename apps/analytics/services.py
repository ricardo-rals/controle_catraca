from typing import List, Dict, Any
from django.db.models import Count, QuerySet
from django.db.models.functions import ExtractHour, TruncDate
from apps.acessos.models import RegistroAcesso


def picos_por_hora(queryset: QuerySet[RegistroAcesso]) -> List[Dict[str, int]]:
    """
    Agrega os acessos por hora.
    Retorna uma lista com 24 elementos, representando as horas do dia (0 a 23).
    """
    # Inicializa o dicionário com 24 horas zeradas
    resultados_dict = {hora: 0 for hora in range(24)}

    agregado = (
        queryset.annotate(hora=ExtractHour("timestamp"))
        .values("hora")
        .annotate(total=Count("id"))
        .order_by("hora")
    )

    # Preenche com os valores do banco
    for item in agregado:
        if item["hora"] is not None:
            # Garante que o tipo da hora seja inteiro
            hora = int(item["hora"])
            if 0 <= hora < 24:
                resultados_dict[hora] = item["total"]

    # Retorna na formatação esperada
    return [{"hora": hora, "total": total} for hora, total in resultados_dict.items()]


def top_dias(
    queryset: QuerySet[RegistroAcesso], limite: int = 5
) -> List[Dict[str, Any]]:
    """
    Retorna os dias de maior volume de acesso.
    """
    agregado = (
        queryset.annotate(dia=TruncDate("timestamp"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("-total")[:limite]
    )

    return [
        {
            "dia": item["dia"].strftime("%Y-%m-%d") if item["dia"] else None,
            "total": item["total"],
        }
        for item in agregado
    ]


def total_de_acessos(queryset: QuerySet[RegistroAcesso]) -> int:
    """Total de registros no queryset informado.

    Exemplo:
        >>> total_de_acessos(RegistroAcesso.objects.filter(tipo_acesso="Entrada"))
        1234
    """
    return queryset.count()
