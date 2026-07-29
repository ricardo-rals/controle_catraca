# Política de Pseudonimização e LGPD

Este documento descreve como o sistema de Controle de Acesso do Campus (CAC) trata
dados pessoais provenientes das catracas, em conformidade com a LGPD (Lei 13.709/2018).

## 1. Dados coletados

O arquivo exportado da catraca contém, entre outros, os seguintes campos pessoais:

- Número da Credencial (matrícula)
- Nome
- Estrutura Organizacional
- Foto (referência)
- Data e direção do evento, equipamento e ponto de acesso

## 2. O que é armazenado e o que é pseudonimizado

Apenas o **mínimo necessário** é persistido no banco (`RegistroAcesso`):

| Campo de origem | No banco |
|-----------------|----------|
| Número da Credencial | **Cifrado** em `credencial_cifrada` |
| Nome | **Cifrado** em `nome_cifrado` |
| Foto | **Referência (URL) armazenada** em `foto` |
| Data do Evento | `timestamp` |
| Equipamento | `ponto_acesso` (FK) |
| Direção do Evento | `tipo_acesso` (Entrada/Saída) |

A credencial nunca é gravada em texto claro. Ela fica armazenada apenas como
valor cifrado reversível em `credencial_cifrada`, usando um modo determinístico
para viabilizar deduplicação/cruzamento. O nome também não é gravado em
texto claro: fica apenas em `nome_cifrado`. Na interface, **apenas o perfil admin vê a
foto (referência), o identificador completo, a credencial descriptografada e o nome descriptografado**; o gestor vê o identificador
truncado e não acessa a foto (ver seção 4).

## 3. Técnica de pseudonimização

- O salt vem da variável de ambiente/segredo **`PSEUDONIMIZACAO_SALT`**, nunca
  versionado no repositório.
- O valor cifrado da credencial é **determinístico**: a mesma credencial sempre
  gera o mesmo texto cifrado, o que permite cruzar acessos da mesma pessoa e
  deduplicar registros sem armazenar texto claro.
- Trocar o salt invalida o cruzamento histórico; ele deve ser estável por ambiente.
- **Reversível sob autorização:** `credencial_cifrada` e `nome_cifrado` usam
  chaves derivadas do segredo `PSEUDONIMIZACAO_SALT`; a credencial usa AES-SIV
  (determinístico) e o nome usa AES-GCM (não determinístico).

## 4. Quem tem acesso

- O acesso às telas internas exige autenticação (perfil **admin** ou **gestor**).
- A gestão de usuários, as Regras de Horário e o Django Admin são restritos ao
  perfil **admin**.
- **Visibilidade de dados sensíveis por perfil:**
  - **admin:** vê a foto (referência), o identificador completo, a credencial descriptografada e o nome descriptografado.
  - **gestor:** **não** acessa a foto e vê o identificador **truncado**.
- A visualização em texto claro para administradores vem dos campos cifrados
  reversíveis.

> A regra de visibilidade é aplicada no servidor (`apps/usuarios/perfis.py`).

## 5. Retenção e descarte

- Os registros de acesso são mantidos pelo período necessário às finalidades de
  gestão do campus. (Definir prazo institucional.)
- A remoção de uma importação (`Importacao`) remove em cascata seus
  `RegistroAcesso` e falhas associadas.

## 6. Solicitação de remoção

Titulares podem solicitar informações ou remoção de dados pelos canais oficiais do
IFBA. Para localizar os registros de um titular, a credencial informada pelo
solicitante é cifrada com AES-SIV (determinístico) e o resultado é comparado com o
campo `credencial_cifrada`. Como a cifra é determinística, a mesma credencial sempre
produz o mesmo valor, o que permite a busca sem descriptografar a base inteira. A
conferência autorizada pode usar também `nome_cifrado`, descriptografado pelo perfil
admin.
