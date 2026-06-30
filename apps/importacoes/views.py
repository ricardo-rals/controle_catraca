from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import UploadCSVForm
from .models import Importacao


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
