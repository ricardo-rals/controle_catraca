# Decisões de arquitetura (ADRs)

Registro das principais decisões técnicas do projeto, no formato **contexto →
decisão → consequência**. Cada ADR explica *por que* algo é do jeito que é.

---

## ADR-001 — Usuário customizado com campo `perfil` (admin/gestor)

**Contexto:** o sistema tem dois papéis com permissões bem diferentes (administrador
com acesso total; gestor com acesso restrito).

**Decisão:** usar um `AbstractUser` customizado (`UsuarioSistema`) com um campo
`perfil` de escolhas `admin`/`gestor`, em vez de depender só de Groups/Permissions do
Django. O perfil também define `is_staff` (acesso ao Django Admin) no `save()`.

**Consequência:** a regra de acesso fica simples e explícita (`perfil == "admin"`),
reutilizável em mixins/decorators (`PerfilRequeridoMixin`, `perfil_requerido`) e na
regra de visibilidade de dados (`perfis.py`). Custo: um modelo de usuário próprio, que
exige `AUTH_USER_MODEL` definido desde o início.

---

## ADR-002 — De-identificação reversível (AES-SIV) em vez de hash irreversível

**Contexto:** inicialmente a credencial virava um HMAC-SHA256 irreversível — bom para
privacidade, mas impedia o administrador de identificar o titular de um acesso (ex.:
em auditoria). A necessidade de negócio passou a exigir que o **admin veja a credencial
e o nome reais**.

**Decisão:** substituir o hash irreversível por **cifra reversível**:
- **credencial** → `credencial_cifrada` com **AES-SIV** (autenticada e
  **determinística**: a mesma credencial gera sempre o mesmo texto cifrado, preservando
  deduplicação e cruzamento de acessos, e ainda assim descriptografável).
- **nome** → `nome_cifrado` com **AES-GCM** (não determinístico).
- Chaves derivadas do segredo `PSEUDONIMIZACAO_SALT`.

**Consequência:** o admin recupera credencial/nome; o gestor vê a credencial mascarada.
**Trade-off de LGPD:** a proteção ficou **mais fraca** que o hash (agora é reversível por
quem tem o salt) e o sistema passou a **armazenar dado pessoal** (nome + credencial,
cifrados) que antes era descartado. Mitigações: minimização (só admin descriptografa),
o salt vira controle de acesso, e a política está documentada em [`lgpd.md`](lgpd.md).

---

## ADR-003 — Pipeline de importação com Pandas

**Contexto:** os arquivos da catraca (CSV/XLSX) chegam com milhares de linhas,
cabeçalho em português, duplicatas e formatos de data variados.

**Decisão:** processar o arquivo com **pandas** dentro de `ImportacaoService`: ler tudo
como texto, validar cabeçalho/linhas, deduplicar em memória (`drop_duplicates`) e contra
o banco, cifrar credencial/nome e persistir com `bulk_create` em lotes.

**Consequência:** parsing e deduplicação ficam rápidos e concentrados num único serviço,
com contadores de válidos/inválidos/duplicados/atualizados. Custo: pandas é uma dependência
pesada, mas já necessária para os relatórios em Excel.

---

## ADR-004 — WeasyPrint para geração de PDF

**Contexto:** os relatórios precisam de um PDF com layout (cabeçalho, KPIs, tabelas,
rodapé com paginação).

**Decisão:** renderizar um template HTML e convertê-lo em PDF com **WeasyPrint**, em vez
de montar o PDF campo a campo (ex.: ReportLab).

**Consequência:** o layout é feito em HTML/CSS (fácil de manter, mesmo design das telas).
Custo: WeasyPrint precisa de bibliotecas nativas no contêiner (Pango + fontes) e de uma
versão de `pydyf` compatível — ambos fixados no `Dockerfile`/`requirements`.

---

## ADR-005 — Registry genérico de relatórios

**Contexto:** há vários relatórios (acessos, volume, frequentes, picos, fluxo), todos com
filtros próprios e três formatos de saída (PDF/Excel/CSV).

**Decisão:** um **registry** (`apps/relatorios/registry.py`): cada relatório é uma entrada
que sabe se montar a partir do request (colunas, linhas, resumo, form). As telas
(lista/detalhe) e a exportação são **genéricas** e leem do registry.

**Consequência:** adicionar um relatório novo = **uma entrada no registry**, sem nova
view/URL/template. Custo: uma pequena camada de indireção (o "contrato" do `montar`).

---

## ADR-006 — Dashboard interativo com HTMX (sem SPA)

**Contexto:** o dashboard tem filtros de período que devem atualizar os widgets sem
recarregar a página, mas sem a complexidade de uma SPA (React/Vue).

**Decisão:** usar **HTMX**: os filtros disparam um `hx-get` para a própria view
`dashboard`, que devolve só o fragmento de widgets quando a requisição tem o header
`HX-Request`. Os gráficos (Chart.js) re-renderizam no evento `htmx:afterSwap`.

**Consequência:** interatividade com pouco JavaScript, mantendo a renderização no Django.
Custo: cuidado com o ciclo de vida dos gráficos ao trocar o fragmento (destruir/recriar).
