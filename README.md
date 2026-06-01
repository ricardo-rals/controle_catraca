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

Estes são os atalhos que você vai usar com frequência. Existem duas versões, escolha a do seu ambiente: **Makefile** para Linux, Mac ou WSL; **dev.sh** para Git Bash no Windows. As duas fazem exatamente a mesma coisa.

| O que faz | Makefile | dev.sh (Git Bash) |
|---|---|---|
| Sobe o projeto | `make up` | `./dev.sh up` |
| Roda as migrações | `make migrate` | `./dev.sh migrate` |
| Cria migrações | `make makemigrations` | `./dev.sh makemigrations` |
| Cria superusuário | `make createsuperuser` | `./dev.sh createsuperuser` |
| Roda o pre-commit | `make precommit` | `./dev.sh precommit` |
| Roda os testes | `make test` | `./dev.sh test` |
| Terminal no container | `make bash` | `./dev.sh bash` |
| Comando livre | `make cmd="..."` | `./dev.sh exec ...` |

Exemplo de comando livre, para criar uma migração nova:

```bash
make cmd="python manage.py makemigrations"
```

ou

```bash
./dev.sh exec python manage.py makemigrations
```

---

## Qualidade de código

O projeto usa **ruff** e **black** para manter o código padronizado, e **pytest** para os testes. Tudo roda dentro do container, então o resultado é igual para todos, independente do sistema operacional.

A garantia de qualidade acontece em **duas camadas**:

**Camada 1, verificação manual (opcional, na sua máquina).** Antes de commitar, você pode rodar a verificação para já corrigir o que estiver fora do padrão. É opcional, mas recomendado, porque evita que o seu Pull Request seja barrado depois.

```bash
make precommit      # ou ./dev.sh precommit
make test           # ou ./dev.sh test
```

**Camada 2, validação automática no CI (obrigatória, no GitHub).** Quando você abre um Pull Request, o GitHub Actions roda automaticamente o ruff, o black e os testes. Se algo estiver fora do padrão ou algum teste falhar, o Pull Request fica marcado com erro e **não pode ser juntado** até você corrigir. Essa é a rede de segurança: mesmo que alguém esqueça de rodar a verificação manual, o CI barra antes de entrar no projeto.

Você não precisa instalar nada na máquina para isso funcionar. Não há hook de commit local, justamente porque nem todos têm Python instalado. A verificação manual roda no container, e a obrigatória roda no GitHub.

### O que fazer quando o CI acusar erro

1. Abra a aba do Pull Request no GitHub e veja qual etapa falhou.
2. Rode a verificação na sua máquina para reproduzir e corrigir: `make precommit` formata o código, `make test` mostra os testes quebrados.
3. Commite a correção e dê push. O CI roda de novo sozinho.

---

## Fluxo de trabalho com Git

O Git roda na sua máquina, não dentro do container. Esse fluxo se repete para **cada card** do Jira, sempre igual. Decore ele.

**Resumo visual do ciclo:**

```
develop (atualizada) → cria branch → trabalha → commit → push → Pull Request → revisão → merge na develop
```

### 1. Atualize a develop ANTES de criar qualquer branch

Isso é a regra mais importante do fluxo. Sempre que você for começar um card novo, a primeira coisa é garantir que sua develop local está igual à do GitHub. Se você pular esse passo, sua branch parte de uma versão velha e vai dar conflito quando tentar juntar.

```bash
git checkout develop
git pull
```

Se você já estava numa branch de outro card, esse comando te leva para a develop e puxa tudo que o time já juntou. Só depois disso crie a branch nova.

### 2. Crie uma branch para a sua tarefa

O nome segue o padrão `feature/HU-XXX-descricao-curta`. Esse padrão ajuda todo mundo a saber de quem é cada branch e a que card pertence.

```bash
git checkout -b feature/HU-012-configurar-autenticacao
```

Nunca trabalhe direto na develop. Sempre crie uma branch.

### 3. Faça o trabalho

Programe, crie arquivos, o que a tarefa pedir. Use os atalhos do container para rodar o servidor, testes e verificações.

### 4. (Opcional, recomendado) Verifique antes de commitar

Rode a verificação no container para já corrigir o que estiver fora do padrão. Isso evita que seu Pull Request fique vermelho no CI.

```bash
make precommit
make test
```

### 5. Salve com um commit semântico

```bash
git add .
git commit -m "feat(HU-012): configura autenticacao via Django"
```

Se precisar fazer vários commits na mesma branch, tudo bem. Cada commit deve ter uma mensagem descritiva do que foi feito nele.

### 6. Envie para o GitHub

```bash
git push -u origin feature/HU-012-configurar-autenticacao
```

O `-u` só é necessário no primeiro push da branch. Nos seguintes, basta `git push`.

### 7. Abra o Pull Request no GitHub

1. Vá ao repositório no GitHub. O GitHub geralmente mostra um banner amarelo sugerindo "Compare & pull request" logo após o push. Clique nele.
2. **Confira a base:** a base deve ser `develop`, não `main`. Se estiver apontando para `main`, troque no dropdown.
3. **Título:** use o mesmo padrão do commit, ex: `feat(HU-012): configura autenticacao via Django`.
4. **Descrição:** escreva em uma ou duas linhas o que foi feito e cole o link do card no Jira.
5. Clique em **Create pull request**.

O CI roda automaticamente. Se ficar verde, peça revisão de outra pessoa do time. Se ficar vermelho, corrija o que o CI apontou, commite, dê push e o CI roda de novo sozinho.

### 8. Revisão e merge

Outra pessoa do time abre o seu Pull Request, olha o código e, se estiver tudo certo, aprova. Depois clica em **Merge pull request** e confirma. Sua branch é juntada à develop e pode ser deletada.

No Jira, mova o card para **Concluído** e escreva um comentário rápido do que foi entregue.

### Regras importantes

- **Nunca dê push direto na develop ou na main.** Sempre via Pull Request.
- **Nunca faça merge com CI vermelho.** Corrija primeiro.
- **Sempre atualize a develop antes de criar branch.** É o passo 1, não pule.
- **Um card por vez.** Termine ou trave o atual antes de pegar outro.

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

**Meu Pull Request ficou vermelho no GitHub.**
O CI encontrou algo fora do padrão ou um teste quebrado. Abra a aba do Pull Request, veja qual etapa falhou, rode `make precommit` e `make test` na sua máquina para reproduzir e corrigir, depois commite e dê push. O CI roda de novo sozinho.

**Mudei um arquivo e não apareceu no sistema.**
O projeto recarrega sozinho ao salvar. Se não recarregar, confira se o terminal do `make up` ainda está aberto e rodando.

**O terminal abre sempre com `(.venv)` na frente.**
É o VS Code ativando o ambiente virtual automaticamente. Como tudo roda dentro do container, isso é desnecessário e pode confundir. Não atrapalha os comandos, mas se quiser desligar:

1. Abra as configurações do VS Code com `Ctrl + ,`
2. Pesquise por `python.terminal.activateEnvironment`
3. Desmarque a opção

Depois disso, novos terminais abrem sem ativar o `.venv`. O ambiente virtual continua servindo para o editor reconhecer as bibliotecas e não sublinhar os imports de vermelho.

---

## Estrutura de pastas

```
controle-catraca/
  .github/
    workflows/
      ci.yml         pipeline de CI que valida lint, formatação e testes
  config/          configurações do Django (urls, wsgi, asgi e settings/ por ambiente: base, dev, prod)
  apps/            módulos do sistema (usuarios, acessos, importacoes, analytics, relatorios)
  tests/           configuração e factories de testes
  templates/       páginas HTML
  static/          arquivos de estilo, scripts e imagens
  docs/            documentação do projeto
  infra/           arquivos de Docker
  scripts/         utilitários
  requirements/    listas de dependências (base.txt, dev.txt)
  manage.py        ponto de entrada do Django
  pytest.ini       configuração do pytest
  Makefile         atalhos para Linux, Mac, WSL
  dev.sh           atalhos para Windows com Git Bash
  docker-compose.yml
  .env.example     modelo do arquivo de configuração
```

---

Qualquer dúvida que não esteja aqui, traga no canal técnico do time.