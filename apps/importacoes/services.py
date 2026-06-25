import pandas as pd
from django.db import transaction
from django.db.models import Q
import logging

from apps.acessos.models import PontoAcesso, RegistroAcesso
from .utils.pseudonimizacao import criptografar_valor
from .models import Importacao

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

    def processar(self):
        """Ponto de entrada: processa o arquivo CSV e persiste os registros válidos."""
        try:
            with transaction.atomic():
                self._executar_pipeline()
        except Exception as exc:
            logger.exception("Erro inesperado ao processar importação %s", self.importacao.pk)
            self._marcar_como_falha(exc)
            raise

        return self.importacao

    def _executar_pipeline(self):
        # 1. Carregue o CSV com Pandas.
        df = pd.read_csv(self.arquivo)
        
        total_original = len(df)
        
        # Consolidar timestamp
        if 'horario_entrada' in df.columns and 'horario_saida' in df.columns:
            df['timestamp'] = df['horario_entrada'].fillna(df['horario_saida'])
        elif 'horario_entrada' in df.columns:
            df['timestamp'] = df['horario_entrada']
        elif 'horario_saida' in df.columns:
            df['timestamp'] = df['horario_saida']
        else:
            df['timestamp'] = None
            
        df['credencial'] = df.get('identificador_pessoa', None)
        df['ponto_acesso_nome'] = df.get('ponto_acesso', None)
        df['status_acesso'] = df.get('status', '')
        
        # 2. Inválidos: Remova linhas onde credencial ou data/hora estejam vazias.
        df.dropna(subset=['credencial', 'timestamp'], inplace=True)
        self.importacao.total_invalidos = total_original - len(df)
        
        # Tentar converter timestamp para datetime UTC (necessário para banco de dados)
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        invalidos_data = df['timestamp_dt'].isna().sum()
        if invalidos_data > 0:
            df.dropna(subset=['timestamp_dt'], inplace=True)
            self.importacao.total_invalidos += invalidos_data
        
        if df.empty:
            self._finalizar_importacao(df)
            return

        # 3. Transformação 1 (LGPD): Aplique uma função de Hash na coluna de credencial
        df['identificador_pseudonimizado'] = df['credencial'].apply(lambda x: criptografar_valor(str(x).strip()))
        
        # 4. Transformação 2 (FK): Mapeie os nomes dos equipamentos (PontoAcesso)
        nomes_pontos = df['ponto_acesso_nome'].dropna().unique()
        pontos_db = PontoAcesso.objects.filter(nome__in=nomes_pontos)
        mapa_pontos = {p.nome: p.id for p in pontos_db}
        
        pontos_faltantes = set(nomes_pontos) - set(mapa_pontos.keys())
        for nome_ponto in pontos_faltantes:
            if str(nome_ponto).strip():
                novo_ponto = PontoAcesso.objects.create(nome=nome_ponto, localizacao=nome_ponto)
                mapa_pontos[nome_ponto] = novo_ponto.id
            
        df['ponto_acesso_id'] = df['ponto_acesso_nome'].map(mapa_pontos)
        
        # 5. Duplicados Internos: Utilize drop_duplicates do Pandas
        antes_dedup = len(df)
        df.drop_duplicates(subset=['identificador_pseudonimizado', 'timestamp_dt', 'ponto_acesso_id'], inplace=True)
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
            lote = df.iloc[i:i+lote_size]
            q_objects = Q()
            for row in lote[['identificador_pseudonimizado', 'timestamp_dt', 'ponto_acesso_id']].itertuples(index=False):
                if pd.notna(row[2]):
                    q_objects |= Q(
                        identificador_pseudonimizado=row[0],
                        timestamp=row[1],
                        ponto_acesso_id=row[2]
                    )
                else:
                    q_objects |= Q(
                        identificador_pseudonimizado=row[0],
                        timestamp=row[1],
                        ponto_acesso__isnull=True
                    )
            
            if q_objects:
                duplicados_db.extend(
                    RegistroAcesso.objects.filter(q_objects).values_list(
                        'identificador_pseudonimizado', 'timestamp', 'ponto_acesso_id'
                    )
                )
        
        if duplicados_db:
            db_df = pd.DataFrame(list(duplicados_db), columns=['identificador_pseudonimizado', 'timestamp_dt', 'ponto_acesso_id'])
            # Converter timestamp do banco para o mesmo timezone do dataframe
            db_df['timestamp_dt'] = pd.to_datetime(db_df['timestamp_dt'], utc=True)
            
            antes_db_dedup = len(df)
            merged = df.merge(db_df, on=['identificador_pseudonimizado', 'timestamp_dt', 'ponto_acesso_id'], how='left', indicator=True)
            df = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
            
            self.importacao.total_duplicados += (antes_db_dedup - len(df))

        # 7. Finalização
        # Contabilize o que sobrou no DataFrame como total_validos.
        self._finalizar_importacao(df)
        self._inserir_no_banco(df)

    def _finalizar_importacao(self, df):
        self.importacao.total_validos = len(df)
        self.importacao.total_registros = len(df) + self.importacao.total_invalidos + self.importacao.total_duplicados
        self.importacao.status = "SUCESSO"
        self.importacao.motivo_erro = ""
        self.importacao.save(
            update_fields=["total_registros", "total_validos", "total_invalidos", "total_duplicados", "status", "motivo_erro"]
        )

    def _inserir_no_banco(self, df):
        if df.empty:
            return
            
        registros = []
        # Preencher NaNs com strings vazias para colunas de texto
        df['status_acesso'] = df['status_acesso'].fillna('')
        
        for _, row in df.iterrows():
            ponto_acesso_id = None
            if pd.notna(row['ponto_acesso_id']):
                ponto_acesso_id = int(row['ponto_acesso_id'])
                
            registros.append(
                RegistroAcesso(
                    identificador_pseudonimizado=row['identificador_pseudonimizado'],
                    ponto_acesso_id=ponto_acesso_id,
                    tipo_acesso=row['status_acesso'],
                    timestamp=row['timestamp_dt'],
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
