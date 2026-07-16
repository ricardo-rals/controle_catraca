# Schema de Validação de CSV (Importação)

O arquivo importado é o **export padrão da catraca** (CSV com cabeçalho em
Title-Case). As regras abaixo são aplicadas pelo `ImportacaoService`
(`apps/importacoes/services.py`).

## 1. Cabeçalho obrigatório

A primeira linha deve conter os nomes das colunas. As colunas **essenciais** são:

- `Número da Credencial` — obrigatória
- `Data do Evento` — obrigatória (formato `dd/mm/aaaa hh:mm:ss`)

Se qualquer uma faltar, a importação é **abortada** com mensagem clara e marcada
como `FALHA` (nenhum registro é gravado).

## 2. Colunas utilizadas

| Coluna no CSV | Uso no sistema |
|---------------|----------------|
| `Número da Credencial` | Cifrada deterministicamente → `credencial_cifrada` |
| `Data do Evento` | `timestamp` do registro |
| `Equipamento` | Mapeado para `PontoAcesso` (criado se não existir) |
| `Direção do Evento` | `tipo_acesso` (Entrada/Saída) |

Demais colunas do export (Nome, Foto, Área de Origem/Destino etc.) são ignoradas
ou não persistidas — ver [lgpd.md](lgpd.md).

## 3. Tratamento de linhas

- **Linha inválida** (credencial vazia, data vazia ou data não parseável): é
  registrada em `FalhaImportacao` com o número da linha e o motivo, **sem
  interromper** a importação das demais.
- **Duplicada**: descartada quando a tupla
  `(credencial_cifrada, timestamp, ponto_acesso)` já aparece no próprio
  arquivo ou já existe no banco.
- **Válida**: persistida em lote (`bulk_create`) como `RegistroAcesso`.

Ao final, a importação registra os totais: válidos, inválidos e duplicados,
exibidos na tela de resultado (HU-022).
