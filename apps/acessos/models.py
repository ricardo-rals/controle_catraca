from django.db import models
from apps.importacoes.models import Importacao


class PontoAcesso(models.Model):
    # Critério 2 + Mapeamento DBML (equipamento, area_origem, etc)
    nome = models.CharField(max_length=100, help_text="Nome do Equipamento")
    localizacao = models.CharField(max_length=100, help_text="Área de Origem / Destino")
    grupo_equipamento = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Ponto de Acesso"
        verbose_name_plural = "Pontos de Acesso"

    def __str__(self):
        return self.nome


class RegistroAcesso(models.Model):
    # Critério 1 + Mapeamento DBML
    # Aqui aplicaremos um Hash no numero_credencial antes de salvar para respeitar a LGPD
    identificador_pseudonimizado = models.CharField(max_length=255)

    ponto_acesso = models.ForeignKey(PontoAcesso, on_delete=models.SET_NULL, null=True)

    # Mapeando direcao_evento (Ex: Entrada / Saída)
    tipo_acesso = models.CharField(max_length=50)

    # Mapeando data_evento
    timestamp = models.DateTimeField()

    importacao = models.ForeignKey(Importacao, on_delete=models.CASCADE)

    # Campos extras para garantir a integridade com a planilha
    evento = models.CharField(max_length=100, blank=True, null=True)
    foto = models.CharField(max_length=255, blank=True, null=True)
    tipo_consulta = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Registro de Acesso"
        verbose_name_plural = "Registros de Acesso"

    def __str__(self):
        return f"Acesso {self.tipo_acesso} - Credencial {self.identificador_pseudonimizado[:8]}..."
