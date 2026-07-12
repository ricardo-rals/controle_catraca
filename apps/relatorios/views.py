from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font
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
        "queryset": queryset,
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



@login_required
def relatorio_excel(request):

    contexto = _dados_relatorio(request)

    resumo_df = pd.DataFrame(
        [
            {
                "Indicador": "Total de acessos",
                "Valor": contexto["total_acessos"],
            },
            {
                "Indicador": "Pessoas únicas",
                "Valor": contexto["pessoas_unicas"],
            },
        ]
    )

    queryset = contexto["queryset"]

    dados = []

    for registro in queryset:
        dados.append(
            {
                "Identificador": registro.identificador_pseudonimizado,
                "Tipo de Acesso": registro.tipo_acesso,
                "Timestamp": registro.timestamp,
                "Ponto de Acesso": (
                    registro.ponto_acesso.nome
                    if registro.ponto_acesso
                    else ""
                ),
            }
        )

    dados_df = pd.DataFrame(dados)

    #cria o arquio excel em memoria
    output= BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resumo_df.to_excel(writer,sheet_name="Resumo",index=False,)
        dados_df.to_excel(writer,sheet_name="Dados",index=False,)
        ws_resumo = writer.sheets["Resumo"]
        ws_dados = writer.sheets["Dados"]

        for cell in ws_resumo[1]:
            cell.font = Font(bold=True)

        for cell in ws_dados[1]:
            cell.font = Font(bold=True)

        for coluna in ws_resumo.columns:
            tamanho= max(len(str(cell.value)) if cell.value else 0 for cell in coluna)
            ws_resumo.column_dimensions[coluna[0].column_letter].width = tamanho + 2
    
        for coluna in ws_dados.columns :
            tamanho= max(len(str(cell.value)) if cell.value else 0 for cell in coluna)
            ws_dados.column_dimensions[coluna[0].column_letter].width = tamanho + 2
    
        linha_total= ws_dados.max_row + 1

        ws_dados.cell(row=linha_total, column=1, value="TOTAL")
    
        ws_dados.cell(row=linha_total, column=2,value=len(dados_df))

        ws_dados.cell(row=linha_total, column=1).font= Font(bold=True)
        ws_dados.cell(row=linha_total,column=2).font= Font(bold=True)

    output.seek(0)

    
    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

    response["Content-Disposition"] = (
        'attachment; filename="relatorio_acessos.xlsx"'
    )

    return response
