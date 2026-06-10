"""
Módulo de pseudonimização de dados pessoais — LGPD Art. 13

Critérios de aceite (Atualizados):
  (1) Nome completo, credencial e foto criptografados com AES (reversível para auditoria autorizada/ADM)
  (2) Política documentada em docs/lgpd.md
  (3) Cruzamento de acessos via descriptografia sob demanda (auditoria)
  (4) Função de descriptografia reversível para casos autorizados (ex: auditoria interna)
  (5) Função única para criptografar os dados recebendo objeto

Uso (sem main.py):
    python src/pseudonimizacao.py dados_exemplo.csv
"""

import hashlib

# CORREÇÃO: Biblioteca hmac removida, pois não usaremos mais hash irreversível.
import os
import csv
import json
import logging
import sys
import base64
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Salt e chave AES
# ---------------------------------------------------------------------------


def _obter_salt() -> bytes:
    """Obtém o salt da variável de ambiente PSEUDONIMIZACAO_SALT."""
    salt = os.environ.get("PSEUDONIMIZACAO_SALT", "").strip()
    if not salt:
        raise EnvironmentError(
            "Variável de ambiente PSEUDONIMIZACAO_SALT não definida ou vazia.\n"
            "Exemplo: export PSEUDONIMIZACAO_SALT='seu_salt_secreto'"
        )
    return salt.encode("utf-8")


def _obter_chave_aes() -> bytes:
    """
    Deriva uma chave AES-256 a partir do salt usando SHA-256.
    A chave nunca é armazenada — gerada na hora a partir do salt.
    """
    return hashlib.sha256(_obter_salt()).digest()  # 32 bytes = AES-256


# ---------------------------------------------------------------------------
# CORREÇÃO: Funções genéricas de criptografia reversível
# ---------------------------------------------------------------------------


def criptografar_valor(valor: str) -> str:
    """
    Criptografa um valor genérico com AES-GCM (reversível).
    Substitui as antigas funções de hash e criptografia específica.
    """
    if not valor or not str(valor).strip():
        return valor

    chave = _obter_chave_aes()
    aesgcm = AESGCM(chave)
    nonce = os.urandom(12)  # 96 bits — único por operação
    cifrado = aesgcm.encrypt(nonce, str(valor).strip().encode("utf-8"), None)
    return base64.b64encode(nonce + cifrado).decode("utf-8")


def descriptografar_valor(valor_cifrado: str) -> str:
    """
    Descriptografa um valor criptografado — para auditoria autorizada.
    """
    if not valor_cifrado or not str(valor_cifrado).strip():
        return valor_cifrado

    try:
        dados = base64.b64decode(valor_cifrado.encode("utf-8"))
        nonce = dados[:12]
        cifrado = dados[12:]
        chave = _obter_chave_aes()
        aesgcm = AESGCM(chave)
        return aesgcm.decrypt(nonce, cifrado, None).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Falha ao descriptografar valor: {e}")


# ---------------------------------------------------------------------------
# Estrutura de dados pseudonimizada
# ---------------------------------------------------------------------------


@dataclass
class RegistroPseudonimizado:
    """
    Registro pronto para o banco.

    CORREÇÃO: Nomes dos campos atualizados de _hash para _cifrada(o)
    para refletir que agora são dados reversíveis (AES).
    """

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


# ---------------------------------------------------------------------------
# Critério (7) — Função única para criptografar recebendo objeto
# ---------------------------------------------------------------------------


def criptografar_objeto(registro: dict) -> RegistroPseudonimizado:
    """
    Função única que recebe um objeto (dict) com os dados brutos
    e retorna o registro completamente protegido.

    CORREÇÃO: Aplica automaticamente a função genérica `criptografar_valor`
    para o nome, credencial e foto (todos reversíveis agora).
    """
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
        raise KeyError(f"Campos obrigatórios ausentes: {faltando}")

    return RegistroPseudonimizado(
        nome_cifrado=criptografar_valor(registro["nome"]),
        credencial_cifrada=criptografar_valor(registro["numero_credencial"]),
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


# ---------------------------------------------------------------------------
# Leitura do CSV e pseudonimização em lote
# ---------------------------------------------------------------------------


def processar_csv(caminho_csv: str | Path) -> list[RegistroPseudonimizado]:
    """
    Lê o CSV e retorna lista de registros pseudonimizados.
    Linhas inválidas são logadas e puladas sem interromper o lote.
    """
    caminho = Path(caminho_csv)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    registros: list[RegistroPseudonimizado] = []
    erros: list[dict] = []

    # CORREÇÃO: Removido o erro de sintaxe ('encodin\nwith') que havia na linha abaixo
    with caminho.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, linha in enumerate(reader, start=2):
            try:
                reg = criptografar_objeto(dict(linha))
                registros.append(reg)
            except (KeyError, ValueError) as e:
                erros.append({"linha": i, "erro": str(e)})
                logger.warning("Linha %d ignorada: %s", i, e)

    logger.info(
        "CSV processado: %d registros pseudonimizados, %d erros.",
        len(registros),
        len(erros),
    )
    if erros:
        logger.warning("Erros: %s", json.dumps(erros, ensure_ascii=False))

    return registros


# ---------------------------------------------------------------------------
# Critério (3) — Verificação para cruzamento de acessos
# ---------------------------------------------------------------------------


def verificar_credencial(numero_credencial: str, credencial_cifrada: str) -> bool:
    """
    CORREÇÃO: Como abandonamos o hash, para verificar uma credencial
    nós a descriptografamos e comparamos em texto claro.
    """
    try:
        credencial_original = descriptografar_valor(credencial_cifrada)
        return credencial_original == numero_credencial.strip()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Execução direta — sem precisar do main.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # Define salt padrão caso a variável de ambiente não esteja configurada
    if not os.environ.get("PSEUDONIMIZACAO_SALT"):
        os.environ["PSEUDONIMIZACAO_SALT"] = "salt_padrao_desenvolvimento"

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "dados_exemplo.csv"

    logger.info("=== Iniciando pseudonimização LGPD ===")

    try:
        registros = processar_csv(csv_path)
    except (FileNotFoundError, EnvironmentError) as e:
        logger.error("Erro fatal: %s", e)
        sys.exit(1)

    print("\n📋 Registros pseudonimizados prontos para o banco:\n")
    for r in registros:
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
        print("-" * 60)

    # CORREÇÃO: Atualização das variáveis no teste de execução
    if registros:
        print("\n🔍 Cruzamento de acesso (critério 3):\n")
        credencial_teste = (
            "CRED001"  # Ajuste para um valor que exista no seu CSV para teste real
        )
        cifrado_salvo = registros[0].credencial_cifrada
        match = verificar_credencial(credencial_teste, cifrado_salvo)
        print(f"  Credencial '{credencial_teste}' bate com o salvo? → {match}")
        print(f"  Cifrado: {cifrado_salvo[:24]}...  (truncado)\n")

        print("\n🔓 Descriptografia autorizada (critério 6 — auditoria):\n")

        # Testando Nome
        nome_cifrado = registros[0].nome_cifrado
        nome_original = descriptografar_valor(nome_cifrado)
        print(f"  Nome cifrado:   {nome_cifrado[:32]}...  (truncado)")
        print(f"  Nome original:  {nome_original}\n")

        # Testando Foto (Adicionado para demonstração)
        foto_cifrada = registros[0].foto_cifrada
        foto_original = descriptografar_valor(foto_cifrada)
        print(f"  Foto cifrada:   {foto_cifrada[:32]}...  (truncado)")
        print(f"  Foto original:  {foto_original}\n")

    logger.info("=== Concluído: %d registros processados ===", len(registros))
