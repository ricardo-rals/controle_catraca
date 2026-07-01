"""Testes do pipeline de importação de CSV (HU-058).

Cobre parsing, validação de cabeçalho/linha, deduplicação (no CSV e contra o
banco) e pseudonimização determinística. Os CSVs são montados em memória com
io.StringIO usando o cabeçalho real do export da catraca.
"""

import io

import pytest

from django.contrib.auth import get_user_model

from apps.acessos.models import RegistroAcesso
from apps.importacoes.models import Importacao, FalhaImportacao
from apps.importacoes.services import ImportacaoService
from apps.importacoes.utils.pseudonimizacao import pseudonimizar_identificador

User = get_user_model()

HEADER = "Número da Credencial,Data do Evento,Equipamento,Direção do Evento"


def _csv(*linhas):
    return io.StringIO("\n".join([HEADER, *linhas]))


def _nova_importacao():
    user = User.objects.create_user(
        username=f"u{User.objects.count()}", password="Senha12345"
    )
    return Importacao.objects.create(nome_arquivo="t.csv", usuario=user)


def _processar(csv_io):
    imp = _nova_importacao()
    return ImportacaoService(csv_io, imp).processar()


@pytest.mark.django_db
def test_csv_valido_persiste_registros():
    imp = _processar(
        _csv(
            "111,02/06/2026 08:00:00,CATRACA A,Entrada",
            "222,02/06/2026 09:00:00,CATRACA A,Entrada",
        )
    )
    assert imp.status == "SUCESSO"
    assert imp.total_validos == 2
    assert imp.total_invalidos == 0
    assert imp.total_duplicados == 0
    assert RegistroAcesso.objects.filter(importacao=imp).count() == 2


@pytest.mark.django_db
def test_cabecalho_obrigatorio_ausente_aborta():
    csv_io = io.StringIO("Data do Evento,Equipamento\n02/06/2026 08:00:00,CATRACA A")
    imp = _processar(csv_io)
    assert imp.status == "FALHA"
    assert "Cabeçalho inválido" in imp.motivo_erro


@pytest.mark.django_db
def test_campo_vazio_vira_falha():
    imp = _processar(
        _csv(
            ",02/06/2026 08:00:00,CATRACA A,Entrada",  # credencial vazia
            "222,02/06/2026 09:00:00,CATRACA A,Entrada",
        )
    )
    assert imp.total_validos == 1
    assert imp.total_invalidos == 1
    falha = FalhaImportacao.objects.get(importacao=imp)
    assert falha.linha_arquivo == 2  # primeira linha de dados
    assert "credencial vazia" in falha.motivo_erro


@pytest.mark.django_db
def test_data_invalida_vira_falha():
    imp = _processar(
        _csv(
            "111,data-ruim,CATRACA A,Entrada",
            "222,02/06/2026 09:00:00,CATRACA A,Entrada",
        )
    )
    assert imp.total_validos == 1
    assert imp.total_invalidos == 1
    assert "data inválida" in FalhaImportacao.objects.get(importacao=imp).motivo_erro


@pytest.mark.django_db
def test_duplicata_no_csv_descartada():
    imp = _processar(
        _csv(
            "111,02/06/2026 08:00:00,CATRACA A,Entrada",
            "111,02/06/2026 08:00:00,CATRACA A,Entrada",  # idêntica
        )
    )
    assert imp.total_validos == 1
    assert imp.total_duplicados == 1
    assert RegistroAcesso.objects.filter(importacao=imp).count() == 1


@pytest.mark.django_db
def test_duplicata_contra_banco_descartada():
    linha = "111,02/06/2026 08:00:00,CATRACA A,Entrada"
    primeira = _processar(_csv(linha))
    assert primeira.total_validos == 1

    segunda = _processar(_csv(linha))  # mesmo registro, nova importação
    assert segunda.total_validos == 0
    assert segunda.total_duplicados == 1
    # nenhum registro novo no banco além do primeiro
    assert RegistroAcesso.objects.count() == 1


@pytest.mark.django_db
def test_reimportacao_enriquece_registro_com_campos_antes_vazios():
    # 1ª importação: só cabeçalho mínimo, campos extras ficam None no banco.
    primeira = _processar(
        _csv("111,02/06/2026 08:00:00,CATRACA A,Entrada")
    )
    assert primeira.total_validos == 1
    reg = RegistroAcesso.objects.get(importacao=primeira)
    assert reg.evento is None and reg.foto is None

    # 2ª importação: mesma chave (ident+data+ponto), agora com colunas extras.
    header_completo = ",".join(
        [
            "Número da Credencial",
            "Data do Evento",
            "Equipamento",
            "Direção do Evento",
            "Evento",
            "Foto",
            "Tipo de Consulta",
            "Área de Origem",
            "Área de Destino",
        ]
    )
    linha = ",".join(
        [
            "111",
            "02/06/2026 08:00:00",
            "CATRACA A",
            "Entrada",
            "Acesso Concluido em Batch",
            "Ver Imagem",
            "Facial",
            "EXTERNA",
            "INTERNA",
        ]
    )
    segunda = _processar(io.StringIO(header_completo + "\n" + linha))

    assert segunda.total_validos == 0
    assert segunda.total_atualizados == 1
    assert segunda.total_duplicados == 0
    assert RegistroAcesso.objects.count() == 1

    reg.refresh_from_db()
    assert reg.evento == "Acesso Concluido em Batch"
    assert reg.foto == "Ver Imagem"
    assert reg.tipo_consulta == "Facial"
    assert reg.area_origem == "EXTERNA"
    assert reg.area_destino == "INTERNA"


@pytest.mark.django_db
def test_reimportacao_substitui_placeholder_ver_imagem_no_campo_foto():
    header = "Número da Credencial,Data do Evento,Equipamento,Direção do Evento,Foto"
    linha_placeholder = "111,02/06/2026 08:00:00,CATRACA A,Entrada,Ver Imagem"
    linha_url = (
        "111,02/06/2026 08:00:00,CATRACA A,Entrada,"
        "http://mdacesso.local/Handlers/ImageHandler.ashx?id=90925"
    )

    _processar(io.StringIO(header + "\n" + linha_placeholder))
    reg = RegistroAcesso.objects.get()
    assert reg.foto == "Ver Imagem"

    segunda = _processar(io.StringIO(header + "\n" + linha_url))
    assert segunda.total_atualizados == 1

    reg.refresh_from_db()
    assert reg.foto == "http://mdacesso.local/Handlers/ImageHandler.ashx?id=90925"


@pytest.mark.django_db
def test_reimportacao_ja_completa_conta_como_duplicata_pura():
    # 1ª importação com tudo preenchido; 2ª idêntica → duplicata pura.
    header = "Número da Credencial,Data do Evento,Equipamento,Direção do Evento,Evento"
    linha = "111,02/06/2026 08:00:00,CATRACA A,Entrada,Acesso Concluido"
    csv_completo = lambda: io.StringIO(header + "\n" + linha)  # noqa: E731

    _processar(csv_completo())
    segunda = _processar(csv_completo())

    assert segunda.total_atualizados == 0
    assert segunda.total_duplicados == 1


@pytest.mark.django_db
def test_campos_extras_e_grupo_do_equipamento_sao_persistidos():
    from apps.acessos.models import PontoAcesso

    header_completo = ",".join(
        [
            "Número da Credencial",
            "Data do Evento",
            "Equipamento",
            "Direção do Evento",
            "Grupo de Equipamento",
            "Área de Origem",
            "Área de Destino",
            "Evento",
            "Foto",
            "Tipo de Consulta",
        ]
    )
    linha = ",".join(
        [
            "111",
            "02/06/2026 08:00:00",
            "FACIAL CAT 1 ENTRADA",
            "Entrada",
            "PORTARIA",
            "EXTERNA",
            "INTERNA",
            "Acesso Concluido em Batch",
            "Ver Imagem",
            "Facial",
        ]
    )
    csv_io = io.StringIO(header_completo + "\n" + linha)

    imp = _processar(csv_io)
    assert imp.status == "SUCESSO"
    assert imp.total_validos == 1

    reg = RegistroAcesso.objects.get(importacao=imp)
    assert reg.evento == "Acesso Concluido em Batch"
    assert reg.foto == "Ver Imagem"
    assert reg.tipo_consulta == "Facial"
    assert reg.area_origem == "EXTERNA"
    assert reg.area_destino == "INTERNA"

    ponto = PontoAcesso.objects.get(nome="FACIAL CAT 1 ENTRADA")
    assert ponto.grupo_equipamento == "PORTARIA"
    assert ponto.localizacao == "PORTARIA"


def test_pseudonimizacao_deterministica(settings):
    settings.PSEUDONIMIZACAO_SALT = "salt_teste"
    a = pseudonimizar_identificador("69591795")
    b = pseudonimizar_identificador("69591795")
    assert a == b  # determinístico: mesma credencial → mesmo hash
    assert a != "69591795"  # não é o valor original
    assert len(a) == 64  # HMAC-SHA256 hexdigest
