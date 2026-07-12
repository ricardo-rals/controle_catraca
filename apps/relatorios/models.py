from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class RelatorioGerado(models.Model):
    """
    HU-041 — Histórico de relatórios gerados.

    Cada geração de relatório (PDF ou Excel, feita na tela da HU-040)
    cria um registro aqui, guardando os filtros usados e onde o arquivo
    ficou salvo, para permitir baixar de novo sem refazer a consulta.
    """

    # Critério 1: tipo, filtros em JSON, usuario, data, caminho do arquivo

    class Formato(models.TextChoices):
        PDF = "PDF", "PDF"
        EXCEL = "EXCEL", "Excel"

    tipo = models.CharField(
        max_length=100,
        verbose_name="tipo de relatório",
        help_text="Ex: Relatório de acessos, Resumo mensal",
    )

    formato = models.CharField(
        max_length=10,
        choices=Formato.choices,
        verbose_name="formato do arquivo",
    )

    filtros = models.JSONField(
        verbose_name="filtros utilizados",
        help_text="Parâmetros escolhidos pelo usuário na geração (datas, pontos de acesso, etc.)",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="relatorios_gerados",
        verbose_name="usuário",
    )

    data_geracao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="data de geração",
    )

    caminho_arquivo = models.CharField(
        max_length=255,
        verbose_name="caminho do arquivo",
    )

    # Critério 3: arquivos retidos por 30 dias
    DIAS_RETENCAO = 30

    class Meta:
        verbose_name = "relatório gerado"
        verbose_name_plural = "relatórios gerados"
        ordering = ["-data_geracao"]

    def __str__(self):
        return f"{self.tipo} ({self.formato}) - {self.data_geracao:%d/%m/%Y %H:%M}"

    def esta_disponivel(self):
        """
        True se o arquivo ainda está dentro do prazo de retenção (30 dias
        a partir da geração). Usado para habilitar/desabilitar o botão
        "Baixar novamente" na listagem (Critério 3).
        """
        prazo_final = self.data_geracao + timedelta(days=self.DIAS_RETENCAO)
        return timezone.now() <= prazo_final
