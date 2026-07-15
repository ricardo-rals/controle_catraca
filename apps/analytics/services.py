from django.db.models.functions import (
    TruncDay,
    TruncWeek,
    TruncMonth,
    ExtractHour,
    TruncDate,
)

"""Serviço central de métricas analíticas (HU-027).

Contrato comum das funções deste módulo:

1. Cada função recebe um QuerySet de RegistroAcesso já filtrado pela view.
   A view é responsável por aplicar recorte de datas, permissão, etc.
2. Nenhuma função consulta o banco "do zero" nem aplica filtro de data.
3. O retorno é sempre uma estrutura serializável (int, dict, list[dict]),
   pronto para virar JSON no endpoint.
4. Sem side-effects: as funções são puras, testáveis com factory.
"""

from typing import Any, Dict, List

from django.db.models import Count, QuerySet

from apps.acessos.models import RegistroAcesso


def volume_por_periodo(queryset, granularidade: str) -> list[dict]:
    trunc_map = {
        "dia": TruncDay("timestamp"),
        "semana": TruncWeek("timestamp"),
        "mes": TruncMonth("timestamp"),
    }

    if granularidade not in trunc_map:
        raise ValueError("Granularidade inválida. Use 'dia', 'semana' ou 'mes'.")

    resultados = (
        queryset.annotate(periodo=trunc_map[granularidade])
        .values("periodo")
        .annotate(total=Count("id"))
        .order_by("periodo")
    )

    return [
        {"periodo": linha["periodo"], "total": linha["total"]} for linha in resultados
    ]


# CONCERTAR GAMBIARRA ABAIXO
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
    # CONCERTAR GAMBIARRA ABAIXO
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


def fluxo_por_tipo(queryset: QuerySet[RegistroAcesso]) -> List[Dict[str, Any]]:
    """Agrupa os registros de acesso por tipo (Entrada / Saída).

    Retorna uma lista de dicionários com 'tipo' e 'total', ordenada pelo tipo.
    """
    agregado = (
        queryset.values("tipo_acesso")
        .annotate(total=Count("id"))
        .order_by("tipo_acesso")
    )

    return [{"tipo": item["tipo_acesso"], "total": item["total"]} for item in agregado]


def fluxo_por_ponto(queryset: QuerySet[RegistroAcesso]) -> List[Dict[str, Any]]:
    """Agrupa os registros de acesso por ponto de acesso (nome da catraca).

    Retorna uma lista de dicionários com 'ponto' e 'total',
    ordenada pelo nome do ponto.
    """
    agregado = (
        queryset.values("ponto_acesso__nome")
        .annotate(total=Count("id"))
        .order_by("ponto_acesso__nome")
    )

    return [
        {"ponto": item["ponto_acesso__nome"], "total": item["total"]}
        for item in agregado
    ]
