"""Serviço central de métricas analíticas (HU-027).

Contrato comum das funções deste módulo:

1. Cada função recebe um QuerySet de RegistroAcesso já filtrado pela view.
   A view é responsável por aplicar recorte de datas, permissão, etc.
2. Nenhuma função consulta o banco "do zero" nem aplica filtro de data.
3. O retorno é sempre uma estrutura serializável (int, dict, list[dict]),
   pronto para virar JSON no endpoint.
4. Sem side-effects: as funções são puras, testáveis com factory.
"""

import statistics
from datetime import timedelta
from typing import Any, Dict, List

from decouple import config
from django.db.models import (
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    QuerySet,
    Window,
)
from django.db.models.functions import (
    Lag,
    TruncDay,
    TruncWeek,
    TruncMonth,
    ExtractHour,
    ExtractMinute,
    ExtractWeekDay,
    TruncDate,
)
from django.utils import timezone

from apps.acessos.models import RegistroAcesso, RegraHorario

# Intervalo abaixo do qual dois acessos da mesma pessoa no mesmo ponto viram
# anomalia (HU-056). Configurável porque depende do equipamento em campo.
JANELA_REPETICAO_PADRAO = config("ANOMALIA_JANELA_SEGUNDOS", default=60, cast=int)

# Até onde a repetição é comparada: "equipamento" (padrão) ou "grupo".
#
# ponytail: parece um botão a mais, mas a diferença não é cosmética. Num local
# com leitor facial + catraca, uma passagem única gera DOIS registros no mesmo
# grupo com segundos de diferença (FACIAL REFEITORIO -> CATRACA REFEITORIO).
# Comparar por grupo transforma toda entrada normal em anomalia. Por
# equipamento, o preço é perder a pessoa que pula de um portão para outro.
# Escolha depende de como o campus instalou os equipamentos: calibre com dados.
ESCOPO_REPETICAO_PADRAO = config("ANOMALIA_ESCOPO", default="equipamento")

_CAMPO_ESCOPO = {
    "equipamento": "ponto_acesso",
    "grupo": "ponto_acesso__grupo_equipamento",
}


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


def usuarios_frequentes(queryset: QuerySet, limite: int = 20) -> list[dict]:
    """
    Agrupa os registros por credencial cifrada e retorna os usuarios com maior
    numero de ocorrencias no periodo informado.

    A resolucao para exibicao fica na camada de apresentacao, respeitando o
    perfil do usuario.
    """
    resultados = (
        queryset.values("credencial_cifrada")
        .annotate(total=Count("id"))
        .order_by("-total")[:limite]
    )

    return [
        {"credencial": item["credencial_cifrada"], "total": item["total"]}
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


# ---------------------------------------------------------------------------
# Série diária contínua — base da detecção de volume atípico (HU-053)
# ---------------------------------------------------------------------------


def serie_diaria_completa(queryset: QuerySet[RegistroAcesso]) -> List[Dict[str, Any]]:
    """Volume por dia SEM buracos, do primeiro ao último dia com registro.

    `volume_por_periodo` devolve só os dias que têm acesso. A média móvel
    precisa da série contínua: sem isso, um fim de semana some e dias não
    consecutivos são tratados como vizinhos.
    """
    serie = volume_por_periodo(queryset, "dia")
    if not serie:
        return []

    por_dia = {linha["periodo"].date(): linha["total"] for linha in serie}
    inicio, fim = min(por_dia), max(por_dia)

    return [
        {"dia": dia, "total": por_dia.get(dia, 0)}
        for dia in (inicio + timedelta(days=i) for i in range((fim - inicio).days + 1))
    ]


# ---------------------------------------------------------------------------
# HU-053 — detecção de anomalias
# ---------------------------------------------------------------------------


def detectar_volume_atipico(
    serie: List[Dict[str, Any]], janela: int = 30, limiar: float = 2.0
) -> List[Dict[str, Any]]:
    """Dias cujo volume foge da média móvel dos `janela` dias anteriores.

    Recebe a série contínua de `serie_diaria_completa`. Um dia só é avaliado
    quando já existe histórico suficiente antes dele, então os primeiros
    `janela` dias nunca geram alerta.
    """
    achados = []

    for i in range(janela, len(serie)):
        historico = [ponto["total"] for ponto in serie[i - janela : i]]
        media = statistics.fmean(historico)
        desvio = statistics.pstdev(historico)

        # ponytail: série constante não tem desvio; qualquer variação daria
        # "infinitos σ" e alertaria por ruído. Sem σ, sem opinião.
        if desvio == 0:
            continue

        total = serie[i]["total"]
        distancia = abs(total - media)
        if distancia > limiar * desvio:
            achados.append(
                {
                    "dia": serie[i]["dia"],
                    "total": total,
                    "media": round(media, 1),
                    "desvios": round(distancia / desvio, 1),
                }
            )

    return achados


def detectar_fora_de_horario(
    queryset: QuerySet[RegistroAcesso],
) -> List[Dict[str, Any]]:
    """Acessos fora das faixas da RegraHorario, um achado por ocorrência.

    Só olha grupos de equipamento que TÊM regra cadastrada para aquele dia da
    semana: sem regra, não há horário esperado e nada é sinalizado.

    Devolve o id do registro (e não uma contagem diária) porque a tela de
    anomalias precisa chegar até a pessoa que gerou cada acesso.
    """
    regras = list(RegraHorario.objects.all())
    if not regras:
        return []

    minuto_do_dia = ExpressionWrapper(
        ExtractHour("timestamp") * 60 + ExtractMinute("timestamp"),
        output_field=IntegerField(),
    )

    condicao = Q()
    for regra in regras:
        inicio = regra.horario_inicio.hour * 60 + regra.horario_inicio.minute
        fim = regra.horario_fim.hour * 60 + regra.horario_fim.minute
        condicao |= Q(
            ponto_acesso__grupo_equipamento=regra.grupo_equipamento,
            dia_semana=regra.dia_semana,
        ) & (Q(minuto_do_dia__lt=inicio) | Q(minuto_do_dia__gt=fim))

    achados = (
        queryset.annotate(
            # ExtractWeekDay: 1=domingo … 7=sábado, igual ao RegraHorario.DiaSemana.
            dia_semana=ExtractWeekDay("timestamp"),
            minuto_do_dia=minuto_do_dia,
        )
        .filter(condicao)
        .annotate(dia=TruncDate("timestamp"))
        .values("id", "dia", "minuto_do_dia")
        .order_by("dia")
    )

    return [
        {
            "registro_id": item["id"],
            "dia": item["dia"],
            "horario": f"{item['minuto_do_dia'] // 60:02d}:{item['minuto_do_dia'] % 60:02d}",
        }
        for item in achados
    ]


def detectar_acesso_repetido(
    queryset: QuerySet[RegistroAcesso],
    janela_segundos: int = JANELA_REPETICAO_PADRAO,
    escopo: str = ESCOPO_REPETICAO_PADRAO,
) -> List[Dict[str, Any]]:
    """Mesma credencial passando duas vezes dentro da janela (HU-056).

    O pipeline de importação já descarta duplicatas exatas (mesma credencial,
    mesmo instante, mesmo ponto), então o que sobra aqui são leituras
    *próximas*, não idênticas: carona, empréstimo de crachá — ou a catraca
    lendo o crachá duas vezes.

    `escopo` define o que conta como "mesmo lugar": "equipamento" compara cada
    catraca isoladamente; "grupo" compara o local inteiro. Ver a nota em
    ESCOPO_REPETICAO_PADRAO antes de trocar — a diferença gera falso positivo
    em massa onde há leitor facial e catraca no mesmo ponto.

    ponytail: janela e escopo são parâmetros porque catraca real varia de
    instalação. Calibre com os dados antes de confiar no volume de alertas.
    """
    campo_escopo = _CAMPO_ESCOPO.get(escopo)
    if campo_escopo is None:
        raise ValueError(
            f"Escopo inválido: {escopo!r}. Use {' ou '.join(_CAMPO_ESCOPO)}."
        )

    particao = [F("credencial_cifrada"), F(campo_escopo)]
    ordem = F("timestamp").asc()

    achados = (
        queryset.annotate(
            anterior=Window(Lag("timestamp"), partition_by=particao, order_by=ordem),
            anterior_id=Window(Lag("id"), partition_by=particao, order_by=ordem),
        )
        .annotate(
            intervalo=ExpressionWrapper(
                F("timestamp") - F("anterior"), output_field=DurationField()
            )
        )
        .filter(
            intervalo__gt=timedelta(0),
            intervalo__lte=timedelta(seconds=janela_segundos),
        )
        .values("id", "anterior_id", "timestamp", "intervalo")
        .order_by("timestamp")
    )

    return [
        {
            "registro_id": item["id"],
            "registro_anterior_id": item["anterior_id"],
            "dia": timezone.localtime(item["timestamp"]).date(),
            "segundos": int(item["intervalo"].total_seconds()),
        }
        for item in achados
    ]
