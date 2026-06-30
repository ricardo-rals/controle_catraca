import logging

import pandas as pd
from django.db import transaction
from django.db.models import Q

from apps.acessos.models import PontoAcesso, RegistroAcesso
from .utils.pseudonimizacao import pseudonimizar_identificador
from .models import Importacao, FalhaImportacao

logger = logging.getLogger(__name__)

TAMANHO_LOTE = 1000


class ImportacaoService:
    """
    Responsável pelo pipeline de dados (Pandas) e persistência em lote.

    Critérios de aceite (HU-019 e HU-021):
      - Carregar CSV com Pandas
      - Validar e descartar dados inválidos
      - Transformação (LGPD)
      - Mapeamento de chaves estrangeiras (PontoAcesso)
      - Desduplicação em memória (Pandas)
      - Desduplicação contra o banco de dados (Query Otimizada)
      - Inserção via bulk_create em lotes de 1000
    """

    def __init__(self, arquivo, importacao: Importacao):
        self.arquivo = arquivo
        self.importacao = importacao
        self._falhas: list[FalhaImportacao] = []

    def processar(self):
        """
        Ponto de entrada: processa o arquivo CSV e persiste os registros válidos.

        Não re-levanta exceções: em caso de erro a importação fica com status
        FALHA e o motivo preenchido, e a view decide o feedback pelo status.
        """
        try:
            with transaction.atomic():
                self._executar_pipeline()
        except Exception as exc:
            logger.exception(
                "Erro inesperado ao processar importação %s", self.importacao.pk
            )
            self._marcar_como_falha(exc)

        return self.importacao

    # Cabeçalho real do export da catraca (Title-Case com espaços).
    COL_CREDENCIAL = "Número da Credencial"
    COL_DATA = "Data do Evento"
    COL_EQUIPAMENTO = "Equipamento"
    COL_DIRECAO = "Direção do Evento"
    COLUNAS_OBRIGATORIAS = (COL_CREDENCIAL, COL_DATA)

    def _executar_pipeline(self):
        # 1. Carregue o CSV com Pandas (tudo como texto p/ validar antes de converter).
        df = pd.read_csv(self.arquivo, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]

        # HU-018: cabeçalho obrigatório. Coluna essencial ausente aborta com erro claro.
        faltando = [c for c in self.COLUNAS_OBRIGATORIAS if c not in df.columns]
        if faltando:
            raise ValueError(
                "Cabeçalho inválido: coluna(s) obrigatória(s) ausente(s): "
                + ", ".join(faltando)
            )

        # Normaliza para os nomes internos usados pelo restante do pipeline.
        df["credencial"] = df[self.COL_CREDENCIAL]
        df["timestamp"] = df[self.COL_DATA]
        df["ponto_acesso_nome"] = df.get(self.COL_EQUIPAMENTO)
        df["status_acesso"] = df.get(self.COL_DIRECAO, "")

        # 2. Inválidos: registra (linha + motivo) linhas com credencial ou data vazias.
        falta_cred = df["credencial"].isna() | df["credencial"].astype(
            str
        ).str.strip().isin(["", "nan"])
        falta_data = df["timestamp"].isna() | df["timestamp"].astype(
            str
        ).str.strip().isin(["", "nan"])
        for idx in df.index[falta_cred | falta_data]:
            motivos = []
            if falta_cred[idx]:
                motivos.append("credencial vazia")
            if falta_data[idx]:
                motivos.append("data do evento vazia")
            self._registrar_falha(idx, " | ".join(motivos))
        df = df[~(falta_cred | falta_data)]

        # Converte data BR (dd/mm/aaaa hh:mm:ss). Data não parseável vira falha.
        df["timestamp_dt"] = pd.to_datetime(
            df["timestamp"], errors="coerce", dayfirst=True, utc=True
        )
        data_invalida = df["timestamp_dt"].isna()
        for idx in df.index[data_invalida]:
            self._registrar_falha(idx, "data inválida")
        df = df[~data_invalida]

        self.importacao.total_invalidos = len(self._falhas)

        if df.empty:
            self._finalizar_importacao(df)
            return

        # 3. Transformação 1 (LGPD): pseudônimo determinístico da credencial (HU-020)
        df["identificador_pseudonimizado"] = df["credencial"].apply(
            lambda x: pseudonimizar_identificador(str(x).strip())
        )

        # 4. Transformação 2 (FK): Mapeie os nomes dos equipamentos (PontoAcesso)
        nomes_pontos = df["ponto_acesso_nome"].dropna().unique()
        pontos_db = PontoAcesso.objects.filter(nome__in=nomes_pontos)
        mapa_pontos = {p.nome: p.id for p in pontos_db}

        pontos_faltantes = set(nomes_pontos) - set(mapa_pontos.keys())
        for nome_ponto in pontos_faltantes:
            if str(nome_ponto).strip():
                novo_ponto = PontoAcesso.objects.create(
                    nome=nome_ponto, localizacao=nome_ponto
                )
                mapa_pontos[nome_ponto] = novo_ponto.id

        df["ponto_acesso_id"] = df["ponto_acesso_nome"].map(mapa_pontos)

        # 5. Duplicados Internos: Utilize drop_duplicates do Pandas
        antes_dedup = len(df)
        df.drop_duplicates(
            subset=["identificador_pseudonimizado", "timestamp_dt", "ponto_acesso_id"],
            inplace=True,
        )
        self.importacao.total_duplicados = antes_dedup - len(df)

        if df.empty:
            self._finalizar_importacao(df)
            return

        # 6. Confronto com o Banco de Dados
        # Extraia a lista de tuplas únicas que restaram no Pandas.
        # Faça uma query filtrando por essas tuplas em lotes para evitar Q objects gigantes.
        duplicados_db = []
        lote_size = 900
        for i in range(0, len(df), lote_size):
            lote = df.iloc[i : i + lote_size]
            q_objects = Q()
            for row in lote[
                ["identificador_pseudonimizado", "timestamp_dt", "ponto_acesso_id"]
            ].itertuples(index=False):
                if pd.notna(row[2]):
                    q_objects |= Q(
                        identificador_pseudonimizado=row[0],
                        timestamp=row[1],
                        ponto_acesso_id=row[2],
                    )
                else:
                    q_objects |= Q(
                        identificador_pseudonimizado=row[0],
                        timestamp=row[1],
                        ponto_acesso__isnull=True,
                    )

            if q_objects:
                duplicados_db.extend(
                    RegistroAcesso.objects.filter(q_objects).values_list(
                        "identificador_pseudonimizado", "timestamp", "ponto_acesso_id"
                    )
                )

        if duplicados_db:
            db_df = pd.DataFrame(
                list(duplicados_db),
                columns=[
                    "identificador_pseudonimizado",
                    "timestamp_dt",
                    "ponto_acesso_id",
                ],
            )
            # Converter timestamp do banco para o mesmo timezone do dataframe
            db_df["timestamp_dt"] = pd.to_datetime(db_df["timestamp_dt"], utc=True)

            antes_db_dedup = len(df)
            merged = df.merge(
                db_df,
                on=["identificador_pseudonimizado", "timestamp_dt", "ponto_acesso_id"],
                how="left",
                indicator=True,
            )
            df = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

            self.importacao.total_duplicados += antes_db_dedup - len(df)

        # 7. Finalização
        # Contabilize o que sobrou no DataFrame como total_validos.
        self._finalizar_importacao(df)
        self._inserir_no_banco(df)

    def _registrar_falha(self, idx, motivo):
        # idx: índice 0-based do read_csv → linha no arquivo = idx + 2 (cabeçalho + base 1)
        self._falhas.append(
            FalhaImportacao(
                importacao=self.importacao,
                linha_arquivo=int(idx) + 2,
                motivo_erro=motivo,
            )
        )

    def _finalizar_importacao(self, df):
        self.importacao.total_validos = len(df)
        self.importacao.total_registros = (
            len(df) + self.importacao.total_invalidos + self.importacao.total_duplicados
        )
        self.importacao.status = "SUCESSO"
        self.importacao.motivo_erro = ""
        self.importacao.save(
            update_fields=[
                "total_registros",
                "total_validos",
                "total_invalidos",
                "total_duplicados",
                "status",
                "motivo_erro",
            ]
        )
        # Persiste as linhas rejeitadas para a tela de resultado e o CSV de erros (HU-022).
        if self._falhas:
            FalhaImportacao.objects.bulk_create(self._falhas, batch_size=TAMANHO_LOTE)

    def _inserir_no_banco(self, df):
        if df.empty:
            return

        registros = []
        # Preencher NaNs com strings vazias para colunas de texto
        df["status_acesso"] = df["status_acesso"].fillna("")

        for _, row in df.iterrows():
            ponto_acesso_id = None
            if pd.notna(row["ponto_acesso_id"]):
                ponto_acesso_id = int(row["ponto_acesso_id"])

            registros.append(
                RegistroAcesso(
                    identificador_pseudonimizado=row["identificador_pseudonimizado"],
                    ponto_acesso_id=ponto_acesso_id,
                    tipo_acesso=row["status_acesso"],
                    timestamp=row["timestamp_dt"],
                    importacao=self.importacao,
                )
            )

        RegistroAcesso.objects.bulk_create(
            registros,
            batch_size=TAMANHO_LOTE,
        )

    def _marcar_como_falha(self, exc: Exception):
        self.importacao.status = "FALHA"
        self.importacao.motivo_erro = str(exc)[:255]
        self.importacao.save(update_fields=["status", "motivo_erro"])
