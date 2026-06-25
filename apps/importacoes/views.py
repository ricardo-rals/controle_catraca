import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from .forms import UploadCSVForm
from .models import Importacao, FalhaImportacao


@login_required
def importar_csv(request):
    """
    Tela responsável por receber o CSV.

    Nesta versão:
    - recebe o arquivo
    - valida extensão
    - registra a tentativa de importação (com usuário e arquivo)
    - exibe o histórico de importações anteriores
    - NÃO processa os dados (parsing/validação ficam para a HU-018/019,
      que devem chamar ImportacaoService — ponto de integração em services.py)
    """

    if request.method == "POST":

        # salva os dados enviados
        form = UploadCSVForm(request.POST, request.FILES)

        if form.is_valid():

            # pega o arquivo enviado
            arquivo = form.cleaned_data["arquivo"]

            # valida se realmente é csv
            if not arquivo.name.endswith(".csv"):

                messages.error(request, "Envie apenas arquivos CSV.")

                return redirect("importar_csv")

            # registra a tentativa de importação com os metadados (HU-021)
            Importacao.objects.create(
                nome_arquivo=arquivo.name,
                arquivo=arquivo,
                usuario=request.user,
            )

            messages.success(request, "Arquivo recebido com sucesso.")

            return redirect("importar_csv")

    else:
        form = UploadCSVForm()

    # histórico de importações anteriores (HU-017, critério 1)
    importacoes = Importacao.objects.order_by("-data_tentativa")[:20]

    return render(
        request,
        "importacoes/importar_csv.html",
        {"form": form, "importacoes": importacoes},
    )


def dashboard_importacoes_view(request, importacao_id=None):
    # Busca o histórico de todas as importações (as mais recentes primeiro)
    importacoes = Importacao.objects.all().order_by('-id')
    
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
        'importacoes': importacoes,
        'importacao': importacao_selecionada,
        'falhas': falhas,
    }
    return render(request, 'importacoes/detalhe_importacao.html', context)


def exportar_erros_csv_view(request, importacao_id):
    importacao = get_object_or_404(Importacao, id=importacao_id)
    falhas = importacao.falhas.all()
    
    # Configura a resposta HTTP para um arquivo CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="erros_importacao_{importacao.id}.csv"'
    
    writer = csv.writer(response)
    
    # Escreve o cabeçalho
    writer.writerow(['Linha do Arquivo', 'Motivo do Erro'])
    
    # Escreve os dados das linhas rejeitadas
    for falha in falhas:
        writer.writerow([falha.linha_arquivo, falha.motivo_erro])
        
    return response
