from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import UploadCSVForm
from .models import Importacao


def importar_csv(request):
    """
    Tela responsável por receber o CSV.

    Nesta primeira versão:
    - recebe o arquivo
    - valida extensão
    - registra a importação
    - NÃO processa os dados
    """

    if request.method == "POST":

        # salva os dados enviados
        form = UploadCSVForm(request.POST, request.FILES)

        if form.is_valid():

            # pega o arquivo enviado
            arquivo = form.cleaned_data["arquivo"]

            # valida se realmente é csv
            if not arquivo.name.endswith(".csv"):

                messages.error(
                    request,
                    "Envie apenas arquivos CSV."
                )

                return redirect("importar_csv")

            # registra a tentativa de importação
            Importacao.objects.create(nome_arquivo=arquivo.name)

            messages.success(request,"Arquivo recebido com sucesso.")

            return redirect("importar_csv")

    else:
        form = UploadCSVForm()

    return render(request, "importacoes/importar_csv.html",{"form": form})