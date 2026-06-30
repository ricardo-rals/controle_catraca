from django.db import transaction
import logging
import pandas as pd

from apps.acessos.models import PontoAcesso, RegistroAcesso
from .utils.pseudonimizacao import criptografar_valor
from .models import Importacao

logger = logging.getLogger(__name__)

TAMANHO_LOTE = 1000


class ImportacaoService:
    """
    Responsável pela persistência em lote dos registros de acesso importados.

    Critérios de aceite (HU-021):
      1. Inserção via bulk_create em lotes de 1000.
      2. Toda importação dentro de transaction.atomic().
      3. Model Importacao registra metadados (arquivo, data, totais, usuário).
      4. Erro inesperado marca importação como falha com mensagem."""

    def __init__(self, importacao: Importacao, registros_validos: list[dict]):
        self.importacao = importacao
        self.registros_validos = registros_validos

    def processar(self):
        """Ponto de entrada: monta as instâncias e persiste em lote."""
        try:
            with transaction.atomic():
                registros, total_linhas = self._montar_registros()

                RegistroAcesso.objects.bulk_create(
                    registros,
                    batch_size=TAMANHO_LOTE,
                )

                self.importacao.total_registros = total_linhas
                self.importacao.status = self.importacao.STATUS_CHOICES[0][
                    0
                ]  # 'SUCESSO'
                self.importacao.motivo_erro = ""
                self.importacao.save(
                    update_fields=["total_registros", "status", "motivo_erro"]
                )

        except Exception as exc:
            logger.exception(
                "Erro inesperado ao processar importação %s", self.importacao.pk
            )
            self._marcar_como_falha(exc)
            raise

        return self.importacao

    def _montar_registros(self):
        """
        Monta a lista de instâncias de RegistroAcesso apenas em memória
        (sem salvar ainda), a partir dos registros já validados pela
        HU-018/HU-019.

        Para cada registro:
          - criptografa o identificador_pessoa (AES-GCM, HU-020)
          - resolve/cria o PontoAcesso correspondente
          - monta a instância RegistroAcesso vinculada a esta Importacao
        """
        registros = []
        total_linhas = 0

        # Cache de PontoAcesso para evitar N queries repetidas
        cache_pontos = {}

        for dado in self.registros_validos:
            total_linhas += 1

            nome_ponto = (dado.get("ponto_acesso") or "").strip()
            ponto_acesso = cache_pontos.get(nome_ponto)
            if ponto_acesso is None and nome_ponto:
                ponto_acesso, _ = PontoAcesso.objects.get_or_create(
                    nome=nome_ponto,
                    defaults={"localizacao": nome_ponto},
                )
                cache_pontos[nome_ponto] = ponto_acesso

            identificador_em_claro = (dado.get("identificador_pessoa") or "").strip()

            registros.append(
                RegistroAcesso(
                    identificador_pseudonimizado=criptografar_valor(
                        identificador_em_claro
                    ),
                    ponto_acesso=ponto_acesso,
                    tipo_acesso=dado.get("status", ""),
                    timestamp=dado.get("horario_entrada") or dado.get("horario_saida"),
                    importacao=self.importacao,
                )
            )

        return registros, total_linhas

    def _marcar_como_falha(self, exc: Exception):
        self.importacao.status = "FALHA"
        self.importacao.motivo_erro = str(exc)[:255]
        self.importacao.save(update_fields=["status", "motivo_erro"])

    def validar_e_processar_csv(arquivo_obj):
        COLUNAS_OBRIGATORIAS = [
        'Número da Credencial', 'Nome', 'Data do Evento', 'Estrutura Organizacional'
        'Grupo de Equipamento', 'Área de Origem', 'Área de Destino', 'Equipamento',
        'Evento', 'Direção do Evento', 'Tipo de Consulta'
        ]

        """
        Lê um arquivo CSV, valida a existência do cabeçalho e separa 
        as linhas perfeitas das linhas com defeito.
        """
        resultado = {
            "sucesso": True,
            "erro_fatal": None,
            "linhas_validas": [],
            "linhas_invalidas": []
        }

        try:
            df = pd.read_csv(arquivo_obj, dtype=str)
        except Exception as e:
            resultado["sucesso"] = False
            resultado["erro_fatal"] = f"Não foi possível ler o arquivo. Verifique se é um CSV válido. Erro: {str(e)}"
            return resultado

        colunas_do_arquivo = [coluna.strip().lower() for coluna in df.columns]

        for coluna_esperada in COLUNAS_OBRIGATORIAS:
            if coluna_esperada not in colunas_do_arquivo:
                resultado["sucesso"] = False
                resultado["erro_fatal"] = f"A coluna obrigatória '{coluna_esperada}' não foi encontrada no cabeçalho."
                return resultado

        for index, linha in df.iterrows():
            linha_em_formato_dicionario = linha.to_dict()
            numero_da_linha_no_excel = index + 2  # +1 do cabeçalho, +1 porque programador começa a contar do zero

            erros_desta_linha = []

            for coluna in COLUNAS_OBRIGATORIAS:
                valor = linha_em_formato_dicionario.get(coluna)
                if pd.isna(valor) or str(valor).strip() == "":
                    erros_desta_linha.append(f"O campo '{coluna}' está vazio.")

            if erros_desta_linha:
                resultado["linhas_invalidas"].append({
                    "linha": numero_da_linha_no_excel,
                    "dados": linha_em_formato_dicionario,
                    "motivo": " | ".join(erros_desta_linha)
                })
            else:
                resultado["linhas_validas"].append(linha_em_formato_dicionario)

        return resultado