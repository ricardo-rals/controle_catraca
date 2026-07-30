# Política de Pseudonimização e LGPD

Este documento descreve como o sistema de Controle de Acesso do Campus (CAC) trata dados pessoais provenientes das catracas, em conformidade com a Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018).

## 1. Dados Coletados

O arquivo exportado da catraca contém, entre outros, os seguintes campos de identificação pessoal e de tráfego:

- Número da Credencial (matrícula ou identificador de acesso)
- Nome do portador
- Estrutura Organizacional
- Foto (referência/caminho da imagem)
- Data e direção do evento (Entrada/Saída), equipamento utilizado e ponto de acesso

## 2. Armazenamento e Cifragem

Para garantir a segurança da informação e a privacidade dos titulares, o sistema armazena apenas o mínimo necessário no banco de dados (`RegistroAcesso`). Dados de identificação direta nunca são gravados em texto claro:

| Campo de Origem | No Banco de Dados | Técnica de Proteção |
| :--- | :--- | :--- |
| **Número da Credencial** | `credencial_cifrada` | Cifrada de forma determinística (AES-SIV) |
| **Nome** | `nome_cifrado` | Cifrado de forma não-determinística (AES-GCM) |
| **Foto** | `foto` | Referência/URL em texto claro (acesso restrito por perfil na aplicação) |
| **Estrutura Organizacional** | `estrutura_organizacional` | Texto claro (armazenado na tabela `Pessoa`) |
| **Data do Evento** | `timestamp` | Datetime (`DateTimeField`) |
| **Equipamento/Ponto** | `ponto_acesso` | Chave Estrangeira (`ForeignKey`) |
| **Direção do Evento** | `tipo_acesso` | Texto claro ("Entrada" / "Saída") |

> A credencial e o nome permanecem cifrados no banco de dados. A descriptografia ocorre sob demanda na camada de aplicação e apenas para usuários autenticados com nível de acesso adequado (`admin`).

## 3. Técnica de Proteção e Cifragem

O sistema implementa criptografia simétrica reversível utilizando duas abordagens para chaves derivadas do segredo de ambiente **`PSEUDONIMIZACAO_SALT`**:

1. **Cifragem Determinística (AES-SIV de 512 bits)**:
   * **Aplicação**: Utilizada no campo `credencial_cifrada`.
   * **Funcionamento**: A mesma credencial original sempre gerará o mesmo texto cifrado.
   * **Finalidade**: Permite que o sistema realize deduplicação, contagem de pessoas únicas e cruzamento de registros do mesmo titular entre diferentes importações sem expor o valor original e sem necessitar de uma coluna de hash irreversível.

2. **Cifragem Não-Determinística (AES-GCM de 256 bits)**:
   * **Aplicação**: Utilizada no campo `nome_cifrado`.
   * **Funcionamento**: Utiliza um vector de inicialização (nonce) de 12 bytes gerado de forma aleatória a cada gravação. A mesma entrada gerará ciphertexts distintos a cada cifragem.
   * **Finalidade**: Mitiga ataques de frequência e análise de padrões em nomes comuns.

3. **Gestão do Salt**:
   * O segredo `PSEUDONIMIZACAO_SALT` reside unicamente no ambiente de execução do servidor (`.env`) e **nunca** é versionado no repositório Git.

### 3.1 Implicações da Cifragem Reversível sob a LGPD

> **Sobre a Reversibilidade**: A técnica adotada é a *pseudonimização reversível* (criptografia) e não a anonimização definitiva. Quem detém acesso ao segredo `PSEUDONIMIZACAO_SALT` e às chaves de aplicação é capaz de reverter todos os ciphertexts e identificar os titulares. A proteção das identidades repousa na governança e segurança do segredo de ambiente e nas credenciais do servidor.

* **Armazenamento de Dados Pessoais (PII)**: O sistema armazena dados de identificação (nome e credencial cifrados) para atender à **finalidade legítima** de auditoria de acessos e segurança patrimonial do campus (garantindo que um administrador possa identificar o titular em caso de incidentes).
* **Minimização**: O acesso aos dados em texto claro é estritamente segregado por perfis de usuário diretamente na regra de negócio do servidor.

## 4. Matriz de Controle de Acesso e Perfis

O acesso aos dados descriptografados é restrito a usuários autenticados e varia conforme o perfil cadastrado no sistema (`UsuarioSistema`):

* **Administrador (`admin`)**:
  * Acesso completo de leitura e administração.
  * Visualiza dados sensíveis descriptografados: **credencial completa**, **nome completo original** e **foto**.
  * Acesso exclusivo ao Django Admin, gestão de usuários e Regras de Horário.
* **Gestor (`gestor`)**:
  * Perfil estritamente operacional de monitoramento e relatórios.
  * Visualiza dados de forma mascarada/restrita:
    * **Credencial Mascarada**: Apenas os 4 últimos dígitos são exibidos em claro (ex: `******1234`). Credenciais com 4 caracteres ou menos são totalmente substituídas por asteriscos (`****`).
    * **Nome Oculto**: Substituído pelo caractere padrão (`—`).
    * **Sem Foto**: O acesso à visualização da foto é bloqueado.

> A regra de visibilidade e mascaramento é executada estritamente no backend (`apps/usuarios/perfis.py`). O navegador de um usuário com perfil `gestor` nunca recebe os dados em texto claro ou o ciphertext cru, eliminando o risco de vazamento por inspeção do código-fonte HTML ou requisições HTTP.

## 5. Retenção e Descarte de Dados

* **Prazo de Retenção**: Os registros de acesso e dados cifrados dos titulares são mantidos pelo período institucional recomendado para fins de auditoria interna de tráfego e segurança do IFBA.
* **Fluxo de Exclusão**: Não há rotina de expurgo automático agendado (cronjob). A remoção é realizada em lote pelo administrador ao excluir uma `Importacao`, o que acarreta a deleção em cascata (física) de todos os registros de acesso (`RegistroAcesso`) e falhas associadas no banco de dados.

## 6. Solicitação de Direitos do Titular (Acesso e Exclusão)

Para atender a requisições de consulta ou exclusão de dados pessoais por parte do titular (Art. 18 da LGPD):

1. O operador informa a credencial em claro fornecida pelo titular.
2. O sistema realiza a cifragem determinística da credencial informada utilizando o algoritmo **AES-SIV** e o salt do ambiente (`PSEUDONIMIZACAO_SALT`).
3. O valor cifrado resultante é utilizado para consultar diretamente a coluna `credencial_cifrada` no banco de dados.
4. Isso permite localizar e isolar rapidamente todos os registros de acesso vinculados àquele titular para emissão de relatório ou exclusão, sem a necessidade de varrer ou descriptografar a base de dados inteira.