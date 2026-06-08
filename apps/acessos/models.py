from django.db import models
from apps.importacoes.models import Importacao

class Pessoa(models.Model):
    """Dados originais da pessoa cadastrada no sistema de catracas.
    Acesso restrito por perfil. O RegistroAcesso referencia apenas
    o identificador pseudonimizado, não esta tabela diretamente."""

    numero_credencial = models.CharField(
        max_length=50,
        primary_key=True,
        verbose_name="número da credencial",
    )
    nome = models.CharField(
        max_length=150,
        verbose_name="nome",
    )
    estrutura_organizacional = models.CharField(
        max_length=150,
        verbose_name="estrutura organizacional",
        blank=True,
        default="",
    )

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"

    def __str__(self):
        return f"{self.nome} ({self.numero_credencial})"

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
    class DirecaoEvento(models.TextChoices):
        ENTRADA = "Entrada", "Entrada"
        SAIDA = "Saída", "Saída"

    tipo_acesso = models.CharField(
        max_length=50,
        choices=DirecaoEvento.choices,
        verbose_name="direção do evento",
        blank=True,
        default="",
    )

    # Mapeando data_evento
    timestamp = models.DateTimeField()

    importacao = models.ForeignKey(Importacao, on_delete=models.CASCADE)

    # Campos extras para garantir a integridade com a planilha
    evento = models.CharField(max_length=100, blank=True, null=True)
    foto = models.CharField(max_length=255, blank=True, null=True)
    tipo_consulta = models.CharField(max_length=100, blank=True, null=True)

    area_origem = models.CharField(
        max_length=100,
        verbose_name="área de origem",
        blank=True,
        null=True,
    )
    area_destino = models.CharField(
        max_length=100,
        verbose_name="área de destino",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Registro de Acesso"
        verbose_name_plural = "Registros de Acesso"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["identificador_pseudonimizado", "timestamp"],
                name="idx_ident_timestamp",
            ),
            models.Index(
                fields=["timestamp"],
                name="idx_timestamp",
            ),
            models.Index(
                fields=["tipo_acesso"],
                name="idx_tipo_acesso",
            ),
        ]

    def __str__(self):
        return f"Acesso {self.tipo_acesso} - Credencial {self.identificador_pseudonimizado[:8]}..."

class RegraHorario(models.Model):
    """Horário de funcionamento por grupo de equipamento e dia da semana.
    Acessos fora dessas regras são sinalizados como atípicos."""

    class DiaSemana(models.IntegerChoices):
        DOMINGO = 1, "Domingo"
        SEGUNDA = 2, "Segunda-feira"
        TERCA = 3, "Terça-feira"
        QUARTA = 4, "Quarta-feira"
        QUINTA = 5, "Quinta-feira"
        SEXTA = 6, "Sexta-feira"
        SABADO = 7, "Sábado"

    grupo_equipamento = models.CharField(
        max_length=100,
        verbose_name="grupo do equipamento",
        help_text="Ex: PORTARIA, BIBLIOTECA",
    )
    dia_semana = models.IntegerField(
        choices=DiaSemana.choices,
        verbose_name="dia da semana",
    )
    horario_inicio = models.TimeField(
        verbose_name="horário de início",
    )
    horario_fim = models.TimeField(
        verbose_name="horário de fim",
    )

    class Meta:
        verbose_name = "regra de horário"
        verbose_name_plural = "regras de horário"
        ordering = ["grupo_equipamento", "dia_semana"]
        constraints = [
            models.UniqueConstraint(
                fields=["grupo_equipamento", "dia_semana"],
                name="unique_grupo_dia",
            )
        ]

    def __str__(self):
        return (
            f"{self.grupo_equipamento} - "
            f"{self.get_dia_semana_display()}: "
            f"{self.horario_inicio:%H:%M} às {self.horario_fim:%H:%M}"
        )