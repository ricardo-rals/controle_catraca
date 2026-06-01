# Sistema CAC — Controle de Acesso do Campus

Sistema de análise dos dados das catracas eletrônicas do IFBA. Construído com Django, PostgreSQL e Docker.

Este guia foi escrito para que qualquer pessoa, mesmo sem experiência, consiga rodar o projeto do zero. Siga os passos na ordem.

---

## Visão geral: como o projeto funciona

Tudo roda dentro do **Docker**. Você não precisa instalar Python, Django nem PostgreSQL na sua máquina. O Docker cria um ambiente isolado e idêntico para todo mundo do time, então "na minha máquina funciona" deixa de ser problema.

A única coisa que roda fora do Docker é o **Git**, porque ele usa as suas credenciais pessoais do GitHub.

Para não precisar digitar comandos longos de Docker o tempo todo, o projeto tem dois atalhos: o **Makefile** (para quem usa Linux, Mac ou WSL) e o **dev.sh** (para quem usa Windows com Git Bash). Os dois fazem a mesma coisa, use o que funcionar na sua máquina.

---

## Pré-requisitos

Antes de começar, instale na sua máquina:

1. **Docker Desktop.** Baixe em docker.com, instale e abra. Espere o ícone do Docker ficar verde ou estável antes de continuar.
2. **Git.** Baixe em git-scm.com e instale.
3. **Um editor de código.** Recomendado o VS Code, baixe em code.visualstudio.com.

Para confirmar que Docker e Git estão instalados, abra o terminal e rode:

```bash
docker --version
git --version
```

Se os dois mostrarem um número de versão, está pronto.

---

## Passo a passo para rodar o projeto

### Passo 1 — Clonar o repositório

Isso baixa o código do projeto para a sua máquina.

```bash
git clone https://github.com/SEU-USUARIO/controle-catraca.git
cd controle-catraca
```

Troque `SEU-USUARIO` pelo endereço real do repositório do time.

### Passo 2 — Criar o arquivo de configuração

O projeto precisa de um arquivo com as configurações, chamado `.env`. Existe um modelo pronto chamado `.env.example`. Copie ele:

No Linux, Mac ou Git Bash:
```bash
cp .env.example .env
```

No Windows (Prompt de Comando):
```cmd
copy .env.example .env
```

Pronto, o `.env` está criado com valores que já funcionam para desenvolvimento. Não precisa mudar nada agora.

### Passo 3 — Subir o projeto

Esse comando constrói e liga tudo: o Django e o banco de dados PostgreSQL.

Com Makefile:
```bash
make up
```

Com dev.sh:
```bash
./dev.sh up
```

Na primeira vez demora alguns minutos, porque o Docker baixa e monta tudo. Quando aparecer uma mensagem dizendo que o servidor está rodando, está no ar. Deixe esse terminal aberto.

### Passo 4 — Preparar o banco de dados

Abra um **segundo terminal**, na mesma pasta do projeto, e rode as migrações. Isso cria as tabelas no banco.

Com Makefile:
```bash
make migrate
```

Com dev.sh:
```bash
./dev.sh migrate
```

### Passo 5 — Criar seu usuário administrador

Ainda no segundo terminal, crie seu acesso ao sistema. Cada pessoa cria o seu, na própria máquina.

Com Makefile:
```bash
make createsuperuser
```

Com dev.sh:
```bash
./dev.sh createsuperuser
```

Ele vai pedir um nome de usuário, email e senha. Anote, é com isso que você entra no sistema.

### Passo 6 — Acessar o sistema

Abra o navegador e acesse:

- A aplicação: http://localhost:8000
- A área administrativa: http://localhost:8000/admin

Na área administrativa, entre com o usuário e senha que você criou no passo 5.

Pronto, o projeto está rodando.

---

## Comandos do dia a dia

Estes são os atalhos que você vai usar com frequência. Os dois formatos fazem a mesma coisa.

| O que faz | Com Makefile | Com dev.sh |
|---|---|---|
| Sobe o projeto | `make up` | `./dev.sh up` |
| Roda as migrações | `make migrate` | `./dev.sh migrate` |
| Cria superusuário | `make createsuperuser` | `./dev.sh createsuperuser` |
| Roda o pre-commit | `make precommit` | `./dev.sh precommit` |
| Roda os testes | `make test` | `./dev.sh test` |
| Abre um terminal no container | `make bash` | `./dev.sh bash` |
| Roda qualquer comando | `make cmd="..."` | `./dev.sh exec ...` |

Exemplo de comando livre, para criar uma migração nova:

```bash
make cmd="python manage.py makemigrations"
```

ou

```bash
./dev.sh exec python manage.py makemigrations
```

---

## Qualidade de código: o pre-commit

O projeto usa **ruff** e **black** para manter o código padronizado. Eles rodam **dentro do container**, então não importa qual sistema operacional você usa, o resultado é igual para todos.

Essas ferramentas são disparadas automaticamente toda vez que você faz um commit, através de um hook configurado. Você não precisa rodar nada manualmente: ao commitar, o hook chama o ruff e o black dentro do container, eles verificam e formatam o código, e só então o commit é concluído.

Se as ferramentas corrigirem algum arquivo, o commit é interrompido para você revisar. Nesse caso, basta adicionar os arquivos corrigidos e commitar de novo:

```bash
git add .
git commit -m "feat(HU-XXX): sua mensagem"
```

Se quiser rodar a verificação manualmente, sem commitar, use:

```bash
make precommit
```

### Configuração inicial do hook (uma vez por máquina)

Para o hook automático funcionar, cada pessoa precisa instalá-lo uma vez após clonar o projeto. O pre-commit em si é leve e roda na máquina, mas ele foi configurado para delegar a verificação ao container.

```bash
pip install pre-commit
pre-commit install
```

Depois disso, o hook funciona sozinho em todo commit.

---

## Fluxo de trabalho com Git

O Git roda na sua máquina, não dentro do container. O fluxo para cada tarefa é sempre o mesmo:

### 1. Atualize a branch de integração

```bash
git checkout develop
git pull
```

### 2. Crie uma branch para a sua tarefa

O nome segue o padrão `feature/HU-XXX-descricao-curta`:

```bash
git checkout -b feature/HU-012-configurar-autenticacao
```

### 3. Faça o trabalho

Programe, crie arquivos, o que a tarefa pedir.

### 4. Salve com um commit semântico

```bash
git add .
git commit -m "feat(HU-012): configura autenticacao via Django"
```

O hook do pre-commit roda automaticamente aqui. Se ele formatar algo, rode `git add .` e commite de novo.

### 5. Envie para o GitHub

```bash
git push -u origin feature/HU-012-configurar-autenticacao
```

### 6. Abra o Pull Request

No GitHub, abra um Pull Request com base na branch `develop`. Peça revisão de outra pessoa do time. Só depois da aprovação o código é juntado.

---

## Commits semânticos

Para manter o histórico organizado, todo commit segue o padrão:

```
tipo(HU-XXX): descrição em minúsculas
```

| Tipo | Quando usar | Exemplo |
|---|---|---|
| feat | Nova funcionalidade | feat(HU-018): adiciona parser de CSV |
| fix | Correção de bug | fix(HU-012): corrige erro de login |
| docs | Documentação | docs(HU-006): atualiza o README |
| test | Testes | test(HU-058): adiciona teste do parser |
| chore | Organização ou configuração | chore(HU-005): adiciona ruff e black |
| refactor | Melhora o código sem mudar comportamento | refactor(HU-027): simplifica cálculo |
| style | Apenas formatação | style(HU-023): ajusta indentação |

Use sempre o código do card (HU-XXX) relacionado à tarefa.

---

## Problemas comuns

**O Docker não sobe ou dá erro de porta ocupada.**
Você pode ter outro PostgreSQL rodando na sua máquina na porta padrão. O projeto já usa uma porta alternativa para evitar isso. Se mesmo assim der conflito, confira no `docker-compose.yml` qual porta está mapeada e ajuste no `.env`.

**Erro "connection refused" ao rodar migrate.**
O banco ainda não terminou de subir. Espere alguns segundos depois do `make up` antes de rodar o `make migrate`.

**Esqueci de criar o arquivo .env.**
Volte ao Passo 2. Sem o `.env`, o projeto não sabe como conectar no banco.

**O pre-commit não roda no commit.**
Você provavelmente não instalou o hook. Rode `pip install pre-commit` e `pre-commit install` uma vez.

**Mudei um arquivo e não apareceu no sistema.**
O projeto recarrega sozinho ao salvar. Se não recarregar, confira se o terminal do `make up` ainda está aberto e rodando.

---

## Estrutura de pastas

```
controle-catraca/
  config/          configurações do Django (settings, urls)
  apps/            módulos do sistema (usuarios, importacoes, acessos, etc)
  templates/       páginas HTML
  static/          arquivos de estilo, scripts e imagens
  docs/            documentação do projeto
  infra/           arquivos de Docker
  scripts/         utilitários
  requirements/    listas de dependências
  Makefile         atalhos para Linux, Mac, WSL
  dev.sh           atalhos para Windows com Git Bash
  docker-compose.yml
  .env.example     modelo do arquivo de configuração
```

---

Qualquer dúvida que não esteja aqui, traga no canal técnico do time.