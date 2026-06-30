import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import UploadCSVForm
from .models import Importacao
from .services import ImportacaoService


@login_required
def importar_csv(request):
    """
    Recebe o CSV, valida a extensão, registra a tentativa de importação
    (HU-021) e dispara o pipeline de processamento (HU-018/019/020/021).
    Em sucesso, leva para a tela de resultado (HU-022).
    """

    if request.method == "POST":

        # salva os dados enviados
        form = UploadCSVForm(request.POST, request.FILES)

        if form.is_valid():

            # pega o arquivo enviado
            arquivo = form.cleaned_data["arquivo"]

            # valida extensão aceita (CSV ou Excel)
            EXTENSOES_ACEITAS = (".csv", ".xlsx", ".xls")
            if not arquivo.name.lower().endswith(EXTENSOES_ACEITAS):

                messages.error(
                    request,
                    f"Formato não suportado. Envie apenas arquivos CSV ou XLSX "
                    f"(recebido: {arquivo.name}).",
                )

                return redirect("importar_csv")

            # registra a tentativa de importação com os metadados (HU-021)
            importacao = Importacao.objects.create(
                nome_arquivo=arquivo.name,
                arquivo=arquivo,
                usuario=request.user,
            )

            # processa o arquivo: parsing, validação, dedup, pseudonimização e
            # persistência em lote. O serviço marca status SUCESSO ou FALHA.
            ImportacaoService(importacao.arquivo.path, importacao).processar()

            if importacao.status == "FALHA":
                messages.error(
                    request,
                    f"Não foi possível importar o arquivo: {importacao.motivo_erro}",
                )
                return redirect("importar_csv")

            messages.success(
                request,
                f"Importação concluída: {importacao.total_validos} válidos, "
                f"{importacao.total_invalidos} inválidos, "
                f"{importacao.total_duplicados} duplicados.",
            )
            return redirect("dashboard_detalhe", importacao_id=importacao.id)

    else:
        form = UploadCSVForm()

    # histórico de importações anteriores (HU-017, critério 1)
    importacoes = Importacao.objects.order_by("-data_tentativa")[:20]

    return render(
        request,
        "importacoes/importar_csv.html",
        {"form": form, "importacoes": importacoes},
    )


@login_required
def dashboard_importacoes_view(request, importacao_id=None):
    # Busca o histórico de todas as importações (as mais recentes primeiro)
    importacoes = Importacao.objects.all().order_by("-id")

    importacao_selecionada = None
    falhas = None

    if importacao_id:
        importacao_selecionada = get_object_or_404(Importacao, id=importacao_id)
    elif importacoes.exists():
        # Por padrão, se não for passado um ID, seleciona a importação mais recente
        importacao_selecionada = importacoes.first()

    if importacao_selecionada:
        # Utiliza o related_name 'falhas' definido no model FalhaImportacao
        falhas = importacao_selecionada.falhas.all()

    context = {
        "importacoes": importacoes,
        "importacao": importacao_selecionada,
        "falhas": falhas,
    }
    return render(request, "importacoes/detalhe_importacao.html", context)


@login_required
def exportar_erros_csv_view(request, importacao_id):
    importacao = get_object_or_404(Importacao, id=importacao_id)
    falhas = importacao.falhas.all()

    # Configura a resposta HTTP para um arquivo CSV
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="erros_importacao_{importacao.id}.csv"'
    )

    writer = csv.writer(response)

    # Escreve o cabeçalho
    writer.writerow(["Linha do Arquivo", "Motivo do Erro"])

    # Escreve os dados das linhas rejeitadas
    for falha in falhas:
        writer.writerow([falha.linha_arquivo, falha.motivo_erro])

    return response
