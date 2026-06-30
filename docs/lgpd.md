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
| Número da Credencial | **Pseudonimizado** — `identificador_pseudonimizado` |
| Nome | **Não armazenado** |
| Foto | **Não armazenada** |
| Data do Evento | `timestamp` |
| Equipamento | `ponto_acesso` (FK) |
| Direção do Evento | `tipo_acesso` (Entrada/Saída) |

O **nome completo não é armazenado** no fluxo de importação. A credencial nunca é
gravada em texto claro.

## 3. Técnica de pseudonimização

- O identificador é gerado por **HMAC-SHA256(credencial, salt)** — função
  `pseudonimizar_identificador` em `apps/importacoes/utils/pseudonimizacao.py`.
- O salt vem da variável de ambiente/segredo **`PSEUDONIMIZACAO_SALT`**, nunca
  versionado no repositório.
- O resultado é **determinístico**: a mesma credencial sempre gera o mesmo
  identificador, o que permite cruzar acessos da mesma pessoa e deduplicar
  registros — **sem** ser possível reverter o hash para obter a credencial original.
- Trocar o salt invalida o cruzamento histórico; ele deve ser estável por ambiente.

## 4. Quem tem acesso

- O acesso às telas internas exige autenticação (perfil **admin** ou **gestor**).
- A gestão de usuários e o Django Admin são restritos ao perfil **admin**.
- Como a credencial é pseudonimizada de forma irreversível, nem administradores
  recuperam a matrícula original a partir do banco de acessos.

## 5. Retenção e descarte

- Os registros de acesso são mantidos pelo período necessário às finalidades de
  gestão do campus. (Definir prazo institucional.)
- A remoção de uma importação (`Importacao`) remove em cascata seus
  `RegistroAcesso` e falhas associadas.

## 6. Solicitação de remoção

Titulares podem solicitar informações ou remoção de dados pelos canais oficiais do
IFBA. Como o identificador é irreversível, a localização de registros de um titular
depende do recálculo do HMAC a partir da credencial informada pelo solicitante.
