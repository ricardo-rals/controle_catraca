# Create your models here.
from django.db import models


class Importacao(models.Model):
    arquivo = models.FileField("Arquivo CSV", upload_to="importacoes/")
    data_importacao = models.DateTimeField("Data da Importação", auto_now_add=True)
    status = models.CharField("Status", max_length=50, default="concluido")

    class Meta:
        verbose_name = "Importação"
        verbose_name_plural = "Importações"

    def __str__(self):
        return (
            f"Importação #{self.id} - {self.data_importacao.strftime('%d/%m/%Y %H:%M')}"
        )
