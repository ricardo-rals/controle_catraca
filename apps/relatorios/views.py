from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from apps.acessos.filters import RegistroAcessoFilter
from apps.acessos.models import RegistroAcesso
from apps.analytics.services import (
    fluxo_por_ponto,
    fluxo_por_tipo,
    picos_por_hora,
    total_de_acessos,
)


def _dados_relatorio(request):
    """Aplica os filtros da consulta (reusa o RegistroAcessoFilter da HU-023) e
    monta KPIs + tabelas resumo via o serviço de analytics (HU-027).

    Retorna o dicionário de contexto usado tanto pelo PDF (HU-038) quanto,
    futuramente, pela tela e pelo Excel (HU-039/040).
    """
    filtro = RegistroAcessoFilter(
        request.GET or None,
        queryset=RegistroAcesso.objects.select_related("ponto_acesso"),
    )
    queryset = filtro.qs
    filtros = filtro.form.cleaned_data if filtro.form.is_valid() else {}

    total = total_de_acessos(queryset)
    picos = picos_por_hora(queryset)
    hora_pico = max(picos, key=lambda h: h["total"]) if total else None

    return {
        "gerado_em": timezone.localtime(),
        "usuario": request.user,
        "data_inicio": filtros.get("data_inicio"),
        "data_fim": filtros.get("data_fim"),
        "tipo_acesso": filtros.get("tipo_acesso") or "",
        "ponto_acesso": filtros.get("ponto_acesso"),
        "total_acessos": total,
        "pessoas_unicas": queryset.values("identificador_pseudonimizado")
        .distinct()
        .count(),
        "hora_pico": hora_pico,
        "fluxo_tipo": fluxo_por_tipo(queryset),
        "fluxo_ponto": fluxo_por_ponto(queryset),
    }


@login_required
def relatorio_pdf(request):
    """GET /relatorios/pdf/ — gera o relatório do período em PDF (HU-038).

    Lê os mesmos filtros da consulta (query params), monta os dados via o
    serviço de analytics, renderiza um template HTML e converte para PDF com
    WeasyPrint, devolvendo application/pdf com download automático.
    """
    contexto = _dados_relatorio(request)
    html = render_to_string("relatorios/relatorio_pdf.html", contexto)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    resposta = HttpResponse(pdf, content_type="application/pdf")
    nome = f"relatorio_acessos_{timezone.localdate():%Y%m%d}.pdf"
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resposta
