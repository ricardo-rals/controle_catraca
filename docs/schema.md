# Schema de Validação de CSV (Importação)

Para que o arquivo CSV seja aceito pelo sistema, ele deve seguir estritamente as regras abaixo:

1. **Cabeçalho Obrigatório:** O arquivo deve conter a primeira linha com o nome das colunas.
2. **Colunas Esperadas:** * `matricula` (Texto, Obrigatório)
   * `nome` (Texto, Obrigatório)
   * `documento` (Texto/CPF, Obrigatório)
3. **Comportamento:** Linhas com dados vazios serão ignoradas no banco, mas não travarão a leitura do arquivo.