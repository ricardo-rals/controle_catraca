from django.db import models
from apps.usuarios.models import UsuarioSistema


class Importacao(models.Model):
    # Fundindo o critério 3 com o Log_Importacao do modelo de dados
    nome_arquivo = models.CharField(max_length=150)
    linha_arquivo = models.IntegerField(null=True, blank=True)
    dados_brutos = models.TextField(
        blank=True, null=True, help_text="Linha do CSV em caso de erro"
    )
    motivo_erro = models.CharField(max_length=255, blank=True, null=True)

    #  Metadados
    arquivo = models.FileField()
    data_tentativa = models.DateTimeField(auto_now_add=True)
    total_registros = models.IntegerField(default=0)
    usuario = models.ForeignKey(UsuarioSistema, on_delete=models.CASCADE)

    STATUS_CHOICES = [
        ("SUCESSO", "Sucesso"),
        ("FALHA", "Falha"),
        ("PROCESSANDO", "Processando"),
    ]

    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="PROCESSANDO"
    )

    class Meta:
        verbose_name = "Importação"
        verbose_name_plural = "Importações"

    def __str__(self):
        return f"{self.nome_arquivo} - {self.data_tentativa.strftime('%d/%m/%Y %H:%M')}"
