"""Registry de relatórios (HU-040).

Cada relatório é uma entrada que sabe se montar a partir do request. As telas
(lista/detalhe) e a exportação (PDF/Excel/CSV) são genéricas e leem daqui, então
adicionar um relatório novo = uma entrada nova, sem nova view/url/template.

Cada entrada expõe:
    montar(request) -> dict     constrói os dados (roda só quando o usuário busca)
    form_builder(request) -> form   o form de filtros, para renderizar sem buscar

Contrato de `montar`:
    titulo   str          título do relatório
    periodo  str          rótulo do período filtrado
    colunas  list[str]    cabeçalho da tabela (preview / CSV / aba Dados)
    linhas   list[list]   linhas já formatadas como texto (nada de datetime cru)
    resumo   list[tuple]  [(rótulo, valor)] dos KPIs (aba Resumo / topo do PDF)
"""

from dataclasses import dataclass
from typing import Callable

from django.http import Http404
from django.utils import timezone

from apps.acessos.filters import RegistroAcessoFilter
from apps.acessos.models import RegistroAcesso
from apps.analytics.services import (
    fluxo_por_ponto,
    fluxo_por_tipo,
    picos_por_hora,
    top_dias,
    total_de_acessos,
    usuarios_frequentes,
    volume_por_periodo,
)

from .forms import FrequentesForm, PeriodoForm, VolumeForm


@dataclass
class Relatorio:
    slug: str
    nome: str
    descricao: str
    montar: Callable  # (request) -> dict (contrato acima)
    form_builder: Callable  # (request) -> form bound (filtros, sem buscar dados)


def _rotulo_periodo(data_inicio, data_fim):
    if data_inicio and data_fim:
        return f"{data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y}"
    if data_inicio:
        return f"a partir de {data_inicio:%d/%m/%Y}"
    if data_fim:
        return f"até {data_fim:%d/%m/%Y}"
    return "todos os registros"


def _identificador(user, valor):
    """Gestor vê só os 10 primeiros dígitos do hash + reticências; admin vê o
    hash completo. (Futuro: admin poderá ver o nome descriptografado.)"""
    if getattr(user, "perfil", None) == "gestor":
        return f"{valor[:10]}..."
    return valor


def _queryset_periodo(cleaned):
    """QuerySet de RegistroAcesso recortado por data_inicio/data_fim do form."""
    qs = RegistroAcesso.objects.all()
    if cleaned.get("data_inicio"):
        qs = qs.filter(timestamp__date__gte=cleaned["data_inicio"])
    if cleaned.get("data_fim"):
        qs = qs.filter(timestamp__date__lte=cleaned["data_fim"])
    return qs


# ---------------------------------------------------------------------------
# Relatórios
# ---------------------------------------------------------------------------


def _montar_acessos(request):
    """Registros de acesso — reusa o RegistroAcessoFilter da HU-023."""
    filtro = RegistroAcessoFilter(
        request.GET or None,
        queryset=RegistroAcesso.objects.select_related("ponto_acesso"),
    )
    qs = filtro.qs
    filtros = filtro.form.cleaned_data if filtro.form.is_valid() else {}

    colunas = [
        "Data e hora",
        "Identificador",
        "Equipamento",
        "Grupo",
        "Direção",
        "Área de origem",
        "Área de destino",
        "Evento",
    ]
    linhas = [
        [
            # timestamp é tz-aware; formata como texto local (Excel/CSV não aceitam tz).
            timezone.localtime(r.timestamp).strftime("%d/%m/%Y %H:%M:%S"),
            _identificador(request.user, r.identificador_pseudonimizado),
            r.ponto_acesso.nome if r.ponto_acesso else "",
            (r.ponto_acesso.grupo_equipamento or "") if r.ponto_acesso else "",
            r.get_tipo_acesso_display(),
            r.area_origem or "",
            r.area_destino or "",
            r.evento or "",
        ]
        for r in qs.order_by("-timestamp")
    ]

    total = total_de_acessos(qs)
    picos = picos_por_hora(qs)
    pico = max(picos, key=lambda h: h["total"]) if total else None
    resumo = [
        ("Total de acessos", total),
        (
            "Pessoas únicas",
            qs.values("identificador_pseudonimizado").distinct().count(),
        ),
        ("Horário de pico", f"{pico['hora']:02d}h" if pico else "—"),
    ]

    return {
        "titulo": "Registros de acesso",
        "periodo": _rotulo_periodo(filtros.get("data_inicio"), filtros.get("data_fim")),
        "colunas": colunas,
        "linhas": linhas,
        "resumo": resumo,
    }


def _montar_volume(request):
    """Volume de acessos agregado por dia/semana/mês."""
    form = VolumeForm(request.GET or None)
    cleaned = form.cleaned_data if form.is_valid() else {}
    qs = _queryset_periodo(cleaned)
    granularidade = cleaned.get("granularidade") or "dia"

    serie = volume_por_periodo(qs, granularidade)
    linhas = [[d["periodo"].strftime("%d/%m/%Y"), d["total"]] for d in serie]
    resumo = [
        ("Total de acessos", sum(d["total"] for d in serie)),
        (
            "Granularidade",
            dict(VolumeForm().fields["granularidade"].choices).get(
                granularidade, granularidade
            ),
        ),
    ]

    return {
        "titulo": "Volume por período",
        "periodo": _rotulo_periodo(cleaned.get("data_inicio"), cleaned.get("data_fim")),
        "colunas": ["Período", "Total"],
        "linhas": linhas,
        "resumo": resumo,
    }


def _montar_frequentes(request):
    """Usuários (hash) com mais acessos no período."""
    form = FrequentesForm(request.GET or None)
    cleaned = form.cleaned_data if form.is_valid() else {}
    qs = _queryset_periodo(cleaned)
    limite = cleaned.get("limite") or 20

    dados = usuarios_frequentes(qs, limite=limite)
    linhas = [
        [_identificador(request.user, d["identificador"]), d["total"]] for d in dados
    ]
    resumo = [
        ("Usuários no ranking", len(dados)),
        ("Limite (top N)", limite),
    ]

    return {
        "titulo": "Usuários mais frequentes",
        "periodo": _rotulo_periodo(cleaned.get("data_inicio"), cleaned.get("data_fim")),
        "colunas": ["Identificador", "Total de acessos"],
        "linhas": linhas,
        "resumo": resumo,
    }


def _montar_picos(request):
    """Distribuição de acessos por hora do dia (24h) + top dias."""
    form = PeriodoForm(request.GET or None)
    cleaned = form.cleaned_data if form.is_valid() else {}
    qs = _queryset_periodo(cleaned)

    picos = picos_por_hora(qs)
    linhas = [[f"{p['hora']:02d}h", p["total"]] for p in picos]
    pico = max(picos, key=lambda h: h["total"]) if any(h["total"] for h in picos) else None
    tops = top_dias(qs)
    resumo = [
        ("Horário de pico", f"{pico['hora']:02d}h" if pico else "—"),
        ("Dia de maior volume", tops[0]["dia"] if tops else "—"),
    ]

    return {
        "titulo": "Horários de pico",
        "periodo": _rotulo_periodo(cleaned.get("data_inicio"), cleaned.get("data_fim")),
        "colunas": ["Hora", "Total"],
        "linhas": linhas,
        "resumo": resumo,
    }


def _montar_fluxo(request):
    """Fluxo por ponto de acesso (tabela) + por tipo (resumo)."""
    form = PeriodoForm(request.GET or None)
    cleaned = form.cleaned_data if form.is_valid() else {}
    qs = _queryset_periodo(cleaned)

    pontos = fluxo_por_ponto(qs)
    linhas = [[p["ponto"] or "—", p["total"]] for p in pontos]
    resumo = [("Total de acessos", total_de_acessos(qs))] + [
        (t["tipo"] or "—", t["total"]) for t in fluxo_por_tipo(qs)
    ]

    return {
        "titulo": "Fluxo por tipo e ponto",
        "periodo": _rotulo_periodo(cleaned.get("data_inicio"), cleaned.get("data_fim")),
        "colunas": ["Ponto de acesso", "Total"],
        "linhas": linhas,
        "resumo": resumo,
    }


def _form_acessos(request):
    # queryset none() → o form renderiza sem buscar registros (só o dropdown de pontos).
    return RegistroAcessoFilter(
        request.GET or None, queryset=RegistroAcesso.objects.none()
    ).form


RELATORIOS = {
    "acessos": Relatorio(
        "acessos",
        "Registros de acesso",
        "Listagem dos acessos filtrados, com resumo (total, pessoas únicas e horário de pico).",
        _montar_acessos,
        _form_acessos,
    ),
    "volume": Relatorio(
        "volume",
        "Volume por período",
        "Total de acessos agregado por dia, semana ou mês.",
        _montar_volume,
        lambda request: VolumeForm(request.GET or None),
    ),
    "frequentes": Relatorio(
        "frequentes",
        "Usuários mais frequentes",
        "Ranking dos identificadores com mais acessos no período (top N).",
        _montar_frequentes,
        lambda request: FrequentesForm(request.GET or None),
    ),
    "picos": Relatorio(
        "picos",
        "Horários de pico",
        "Distribuição de acessos por hora do dia e dia de maior volume.",
        _montar_picos,
        lambda request: PeriodoForm(request.GET or None),
    ),
    "fluxo": Relatorio(
        "fluxo",
        "Fluxo por tipo e ponto",
        "Acessos por ponto de acesso, com a composição por tipo (Entrada/Saída).",
        _montar_fluxo,
        lambda request: PeriodoForm(request.GET or None),
    ),
}


def get_relatorio(slug):
    rel = RELATORIOS.get(slug)
    if rel is None:
        raise Http404(f"Relatório '{slug}' não encontrado.")
    return rel
