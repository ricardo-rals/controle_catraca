"""Utilitarios LGPD para cifragem reversivel de dados sensiveis.

A credencial e cifrada de forma deterministica para permitir deduplicacao,
comparacao entre importacoes e contagem de pessoas unicas sem manter um hash
separado no banco. Nome e foto continuam cifrados de forma reversivel, com
cifragem nao deterministica.
"""

import base64
import csv
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, AESSIV

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_GCM_PREFIX = "gcm:"
_SIV_PREFIX = "siv:"
_CREDENCIAL_CONTEXT = b"credencial_cifrada:v1"


def _obter_salt() -> bytes:
    """Obtem o salt de PSEUDONIMIZACAO_SALT."""
    salt = os.environ.get("PSEUDONIMIZACAO_SALT", "").strip()
    if not salt:
        try:
            from django.conf import settings

            salt = (getattr(settings, "PSEUDONIMIZACAO_SALT", "") or "").strip()
        except Exception:
            salt = ""
    if not salt:
        raise EnvironmentError(
            "PSEUDONIMIZACAO_SALT nao definida (nem no ambiente nem no settings).\n"
            "Defina no .env: PSEUDONIMIZACAO_SALT='seu_salt_secreto'"
        )
    return salt.encode("utf-8")


def _obter_chave_aesgcm() -> bytes:
    """Deriva chave AES-256 para cifragem nao deterministica."""
    return hashlib.sha256(_obter_salt()).digest()


def _obter_chave_aessiv() -> bytes:
    """Deriva chave AES-SIV de 512 bits para cifragem deterministica."""
    return hashlib.sha512(_obter_salt()).digest()


def criptografar_valor(valor: str, deterministico: bool = False) -> str:
    """Criptografa um valor de forma reversivel.

    Quando `deterministico=True`, usa AES-SIV para garantir que a mesma
    credencial gere sempre o mesmo valor cifrado, viabilizando comparacao e
    deduplicacao sem expor texto claro.
    """
    if not valor or not str(valor).strip():
        return valor

    texto = str(valor).strip().encode("utf-8")
    if deterministico:
        aessiv = AESSIV(_obter_chave_aessiv())
        cifrado = aessiv.encrypt(texto, [_CREDENCIAL_CONTEXT])
        return _SIV_PREFIX + base64.b64encode(cifrado).decode("utf-8")

    aesgcm = AESGCM(_obter_chave_aesgcm())
    nonce = os.urandom(12)
    cifrado = aesgcm.encrypt(nonce, texto, None)
    return _GCM_PREFIX + base64.b64encode(nonce + cifrado).decode("utf-8")


def descriptografar_valor(valor_cifrado: str) -> str:
    """Descriptografa um valor criptografado, incluindo formato legado."""
    if not valor_cifrado or not str(valor_cifrado).strip():
        return valor_cifrado

    try:
        bruto = str(valor_cifrado).strip()
        if bruto.startswith(_SIV_PREFIX):
            dados = base64.b64decode(bruto[len(_SIV_PREFIX) :].encode("utf-8"))
            aessiv = AESSIV(_obter_chave_aessiv())
            return aessiv.decrypt(dados, [_CREDENCIAL_CONTEXT]).decode("utf-8")

        if bruto.startswith(_GCM_PREFIX):
            bruto = bruto[len(_GCM_PREFIX) :]

        dados = base64.b64decode(bruto.encode("utf-8"))
        nonce = dados[:12]
        cifrado = dados[12:]
        aesgcm = AESGCM(_obter_chave_aesgcm())
        return aesgcm.decrypt(nonce, cifrado, None).decode("utf-8")
    except Exception as exc:
        raise ValueError(f"Falha ao descriptografar valor: {exc}")


@dataclass
class RegistroPseudonimizado:
    """Registro pronto para persistencia protegida no banco."""

    nome_cifrado: str
    credencial_cifrada: str
    data_evento: str
    estrutura_organizacional: str
    grupo_equipamento: str
    area_origem: str
    area_destino: str
    equipamento: str
    evento: str
    direcao_evento: str
    foto_cifrada: str
    tipo_consulta: str
    pseudonimizado_em: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


def criptografar_objeto(registro: dict) -> RegistroPseudonimizado:
    """Recebe dados brutos e retorna o registro protegido."""
    campos_obrigatorios = {
        "numero_credencial",
        "nome",
        "data_evento",
        "estrutura_organizacional",
        "grupo_equipamento",
        "area_origem",
        "area_destino",
        "equipamento",
        "evento",
        "direcao_evento",
        "foto",
        "tipo_consulta",
    }
    faltando = campos_obrigatorios - registro.keys()
    if faltando:
        raise KeyError(f"Campos obrigatorios ausentes: {faltando}")

    return RegistroPseudonimizado(
        nome_cifrado=criptografar_valor(registro["nome"]),
        credencial_cifrada=criptografar_valor(
            registro["numero_credencial"], deterministico=True
        ),
        data_evento=registro["data_evento"].strip(),
        estrutura_organizacional=registro["estrutura_organizacional"].strip(),
        grupo_equipamento=registro["grupo_equipamento"].strip(),
        area_origem=registro["area_origem"].strip(),
        area_destino=registro["area_destino"].strip(),
        equipamento=registro["equipamento"].strip(),
        evento=registro["evento"].strip(),
        direcao_evento=registro["direcao_evento"].strip(),
        foto_cifrada=criptografar_valor(registro["foto"]),
        tipo_consulta=registro["tipo_consulta"].strip(),
    )


def processar_csv(caminho_csv: str | Path) -> list[RegistroPseudonimizado]:
    """Le o CSV e retorna lista de registros cifrados."""
    caminho = Path(caminho_csv)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho}")

    registros: list[RegistroPseudonimizado] = []
    erros: list[dict] = []

    with caminho.open(newline="", encoding="utf-8") as arquivo_csv:
        reader = csv.DictReader(arquivo_csv)
        for i, linha in enumerate(reader, start=2):
            try:
                reg = criptografar_objeto(dict(linha))
                registros.append(reg)
            except (KeyError, ValueError) as exc:
                erros.append({"linha": i, "erro": str(exc)})
                logger.warning("Linha %d ignorada: %s", i, exc)

    logger.info(
        "CSV processado: %d registros cifrados, %d erros.",
        len(registros),
        len(erros),
    )
    if erros:
        logger.warning("Erros: %s", json.dumps(erros, ensure_ascii=False))

    return registros


def verificar_credencial(numero_credencial: str, credencial_cifrada: str) -> bool:
    """Verifica se a credencial informada corresponde ao valor cifrado salvo."""
    try:
        credencial_original = descriptografar_valor(credencial_cifrada)
        return credencial_original == numero_credencial.strip()
    except Exception:
        return False


if __name__ == "__main__":
    if not os.environ.get("PSEUDONIMIZACAO_SALT"):
        os.environ["PSEUDONIMIZACAO_SALT"] = "salt_padrao_desenvolvimento"

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "dados_exemplo.csv"

    logger.info("=== Iniciando cifragem LGPD ===")

    try:
        registros = processar_csv(csv_path)
    except (FileNotFoundError, EnvironmentError) as exc:
        logger.error("Erro fatal: %s", exc)
        sys.exit(1)

    print("\nRegistros cifrados prontos para o banco:\n")
    for registro in registros:
        print(json.dumps(registro.to_dict(), ensure_ascii=False, indent=2))
        print("-" * 60)

    if registros:
        print("\nVerificacao de cruzamento por credencial:\n")
        credencial_teste = "CRED001"
        cifrado_salvo = registros[0].credencial_cifrada
        match = verificar_credencial(credencial_teste, cifrado_salvo)
        print(f"  Credencial '{credencial_teste}' bate com o salvo? -> {match}")
        print(f"  Cifrado: {cifrado_salvo[:24]}...\n")

        print("\nDescriptografia autorizada:\n")
        nome_cifrado = registros[0].nome_cifrado
        nome_original = descriptografar_valor(nome_cifrado)
        print(f"  Nome cifrado:   {nome_cifrado[:32]}...")
        print(f"  Nome original:  {nome_original}\n")

        foto_cifrada = registros[0].foto_cifrada
        foto_original = descriptografar_valor(foto_cifrada)
        print(f"  Foto cifrada:   {foto_cifrada[:32]}...")
        print(f"  Foto original:  {foto_original}\n")

    logger.info("=== Concluido: %d registros processados ===", len(registros))
