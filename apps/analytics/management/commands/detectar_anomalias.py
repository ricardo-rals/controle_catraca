"""Detecta anomalias nos acessos e grava os alertas (HU-053).

Uso:
    ./dev.sh exec python manage.py detectar_anomalias
    ./dev.sh exec python manage.py detectar_anomalias --janela 15 --limiar 1.5

Também roda sozinho ao fim de cada importação bem-sucedida — o volume só muda
quando alguém importa, então não há motivo para agendar por tempo.
"""

from django.core.management.base import BaseCommand

from apps.acessos.models import RegistroAcesso
from apps.analytics.models import Alerta
from apps.analytics.services import (
    ESCOPO_REPETICAO_PADRAO,
    JANELA_REPETICAO_PADRAO,
    _CAMPO_ESCOPO,
    detectar_acesso_repetido,
    detectar_fora_de_horario,
    detectar_volume_atipico,
    serie_diaria_completa,
)

JANELA_PADRAO = 30
LIMIAR_PADRAO = 2.0


def detectar_e_gravar(
    janela=JANELA_PADRAO,
    limiar=LIMIAR_PADRAO,
    janela_repeticao=JANELA_REPETICAO_PADRAO,
    escopo=ESCOPO_REPETICAO_PADRAO,
) -> dict:
    """Roda as três detecções e persiste os alertas. Devolve a contagem.

    Idempotente nos dois formatos: anomalia de dia é única por (data, tipo);
    anomalia de ocorrência é única por (registro, tipo). Rodar de novo
    atualiza, nunca duplica.
    """
    queryset = RegistroAcesso.objects.all()
    criados = {
        Alerta.Tipo.VOLUME_ATIPICO: 0,
        Alerta.Tipo.FORA_DE_HORARIO: 0,
        Alerta.Tipo.ACESSO_REPETIDO: 0,
    }

    serie = serie_diaria_completa(queryset)
    for achado in detectar_volume_atipico(serie, janela=janela, limiar=limiar):
        Alerta.objects.update_or_create(
            data=achado["dia"],
            tipo=Alerta.Tipo.VOLUME_ATIPICO,
            registro=None,
            defaults={
                "valor": achado["total"],
                "detalhe": (
                    f"{achado['total']} acessos, {achado['desvios']}σ da média "
                    f"de {achado['media']} dos {janela} dias anteriores."
                ),
            },
        )
        criados[Alerta.Tipo.VOLUME_ATIPICO] += 1

    for achado in detectar_fora_de_horario(queryset):
        Alerta.objects.update_or_create(
            registro_id=achado["registro_id"],
            tipo=Alerta.Tipo.FORA_DE_HORARIO,
            defaults={
                "data": achado["dia"],
                "valor": 1,
                "detalhe": (
                    f"Acesso às {achado['horario']}, fora da faixa cadastrada "
                    "em Regras de Horário."
                ),
            },
        )
        criados[Alerta.Tipo.FORA_DE_HORARIO] += 1

    for achado in detectar_acesso_repetido(
        queryset, janela_segundos=janela_repeticao, escopo=escopo
    ):
        Alerta.objects.update_or_create(
            registro_id=achado["registro_id"],
            tipo=Alerta.Tipo.ACESSO_REPETIDO,
            defaults={
                "data": achado["dia"],
                "valor": achado["segundos"],
                "registro_anterior_id": achado["registro_anterior_id"],
                "detalhe": (
                    f"Nova passagem {achado['segundos']}s após a anterior, "
                    "com a mesma credencial."
                ),
            },
        )
        criados[Alerta.Tipo.ACESSO_REPETIDO] += 1

    return criados


class Command(BaseCommand):
    help = (
        "Detecta volume atípico, acesso fora de horário e repetido, gravando Alertas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--janela",
            type=int,
            default=JANELA_PADRAO,
            help=f"Dias de histórico da média móvel (padrão: {JANELA_PADRAO}).",
        )
        parser.add_argument(
            "--limiar",
            type=float,
            default=LIMIAR_PADRAO,
            help=f"Desvios padrão para alertar (padrão: {LIMIAR_PADRAO}).",
        )
        parser.add_argument(
            "--janela-repeticao",
            type=int,
            default=JANELA_REPETICAO_PADRAO,
            help=(
                "Segundos entre dois acessos da mesma pessoa no mesmo ponto para "
                f"virar anomalia (padrão: {JANELA_REPETICAO_PADRAO})."
            ),
        )
        parser.add_argument(
            "--escopo",
            choices=sorted(_CAMPO_ESCOPO),
            default=ESCOPO_REPETICAO_PADRAO,
            help=(
                "O que conta como 'mesmo lugar' na repetição "
                f"(padrão: {ESCOPO_REPETICAO_PADRAO})."
            ),
        )

    def handle(self, *args, **opcoes):
        criados = detectar_e_gravar(
            janela=opcoes["janela"],
            limiar=opcoes["limiar"],
            janela_repeticao=opcoes["janela_repeticao"],
            escopo=opcoes["escopo"],
        )

        if not sum(criados.values()):
            self.stdout.write("Nenhuma anomalia encontrada.")
            return

        for tipo, quantidade in criados.items():
            self.stdout.write(
                self.style.SUCCESS(f"{quantidade:>5}  {Alerta.Tipo(tipo).label}")
            )
