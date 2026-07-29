import hashlib
import secrets

from django.db import models


class Alerta(models.Model):
    """Anomalia detectada pelo command `detectar_anomalias` (HU-053/056).

    Duas naturezas convivem aqui:

    - **agregada por dia** (volume atípico): é propriedade da data, não de
      ninguém em particular. `registro` fica nulo.
    - **por ocorrência** (fora de horário, acesso repetido): aponta para o
      `RegistroAcesso` que a gerou, e portanto para uma pessoa. É o que
      permite a tela de anomalias listar quem foi.

    As duas constraints condicionais garantem idempotência nos dois formatos:
    rodar a detecção de novo atualiza, nunca duplica.
    """

    class Tipo(models.TextChoices):
        VOLUME_ATIPICO = "volume_atipico", "Volume atípico"
        FORA_DE_HORARIO = "fora_de_horario", "Acesso fora do horário"
        ACESSO_REPETIDO = "acesso_repetido", "Acesso repetido em sequência"

    data = models.DateField(verbose_name="data do evento")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    valor = models.FloatField(
        help_text="Volume do dia, ou o intervalo em segundos do acesso repetido."
    )
    detalhe = models.CharField(max_length=200, blank=True, default="")
    registro = models.ForeignKey(
        "acessos.RegistroAcesso",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="alertas",
        help_text="Acesso que gerou a anomalia. Nulo em anomalias do dia inteiro.",
    )
    registro_anterior = models.ForeignKey(
        "acessos.RegistroAcesso",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alertas_como_anterior",
        help_text=(
            "Acesso imediatamente antes, no acesso repetido. Guardado para "
            "contar quantas passagens distintas formaram a sequência."
        ),
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        ordering = ["-data", "tipo"]
        constraints = [
            models.UniqueConstraint(
                fields=["data", "tipo"],
                condition=models.Q(registro__isnull=True),
                name="unique_alerta_diario",
            ),
            models.UniqueConstraint(
                fields=["registro", "tipo"],
                condition=models.Q(registro__isnull=False),
                name="unique_alerta_por_registro",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} em {self.data:%d/%m/%Y}"

    @property
    def por_ocorrencia(self) -> bool:
        return self.registro_id is not None


def gerar_chave_api() -> str:
    """Chave nova em texto claro. Só é exibida uma vez, na criação."""
    return f"cac_{secrets.token_urlsafe(32)}"


def hash_chave_api(chave: str) -> str:
    """SHA-256 da chave.

    Chave de API é aleatória e longa, diferente de senha de usuário: não
    precisa de KDF lento, e o hash roda a cada requisição da API pública.
    """
    return hashlib.sha256(chave.strip().encode("utf-8")).hexdigest()


class ChaveAPI(models.Model):
    """Credencial da API pública (HU-055).

    A chave em claro nunca é persistida: guardamos só o SHA-256 e um prefixo
    curto, que serve para o admin reconhecer qual chave é qual.
    """

    nome = models.CharField(
        max_length=100,
        help_text="Quem usa esta chave (ex.: 'Painel da reitoria').",
    )
    prefixo = models.CharField(max_length=12, editable=False)
    chave_hash = models.CharField(max_length=64, unique=True, editable=False)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "chave de API"
        verbose_name_plural = "chaves de API"
        ordering = ["-criado_em"]

    def __str__(self):
        estado = "ativa" if self.ativa else "revogada"
        return f"{self.nome} ({self.prefixo}…, {estado})"

    @classmethod
    def criar(cls, nome: str) -> tuple["ChaveAPI", str]:
        """Cria a chave e devolve (objeto, chave_em_claro).

        A chave em claro só existe neste retorno — depois disso, só o hash.
        """
        chave = gerar_chave_api()
        objeto = cls.objects.create(
            nome=nome,
            prefixo=chave[:12],
            chave_hash=hash_chave_api(chave),
        )
        return objeto, chave
