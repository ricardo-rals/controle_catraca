# Instalação e execução — Sistema CAC

Passo a passo para subir o projeto do zero. **Tudo roda em Docker** — você não precisa
instalar Python nem PostgreSQL na máquina, só o Docker e o Git.

## Pré-requisitos

- **Docker Desktop** (com o daemon rodando).
- **Git**.
- Um editor (VS Code recomendado).

Confirme:

```bash
docker --version
git --version
```

## 1. Clonar o repositório

```bash
git clone <URL-do-repositorio>
cd controle_catraca
```

## 2. Criar o arquivo de configuração `.env`

Existe um modelo `.env.example`. Copie:

```bash
cp .env.example .env      # Linux/Mac/Git Bash
# ou:  copy .env.example .env   (Windows/cmd)
```

Variáveis do `.env`:

| Variável | Para quê | Observação |
|----------|----------|------------|
| `SECRET_KEY` | chave do Django (e assinatura JWT) | **trocar em produção** — não usar o default |
| `DEBUG` | modo desenvolvimento | `True` em dev, `False` em prod |
| `DATABASE_URL` | conexão com o Postgres | já aponta para o contêiner (`...@localhost:5433/cac_db`) |
| `PSEUDONIMIZACAO_SALT` | segredo que deriva a chave de cifra da credencial/nome | **trocar por um valor secreto e estável**; quem tem o salt descriptografa os dados |

> ⚠️ Em desenvolvimento os defaults já funcionam. **Em produção**, gere `SECRET_KEY` e
> `PSEUDONIMIZACAO_SALT` próprios e mantenha-os fora do repositório (`.env` está no `.gitignore`).

## 3. Subir os contêineres

```bash
docker compose up -d      # ou: ./dev.sh up   /   make up
```

Sobe o Django (`cac_web`) e o PostgreSQL (`cac-db`). Na primeira vez demora (baixa e
monta as imagens).

## 4. Preparar o banco

```bash
./dev.sh migrate          # ou: docker compose exec web python manage.py migrate
```

## 5. Criar os usuários de acesso

Seed pronto com um **admin** e um **gestor** de desenvolvimento (idempotente):

```bash
./dev.sh seed             # cria admin / gestor
```

Ou um superusuário próprio:

```bash
./dev.sh createsuperuser
```

## 6. Acessar

- Aplicação: <http://localhost:8000>
- Página de privacidade (pública): <http://localhost:8000/privacidade/>
- Django Admin: <http://localhost:8000/admin> (só perfil admin)

Entre com o usuário criado no passo 5.

## Comandos do dia a dia

| Ação | Comando |
|------|---------|
| Subir o projeto | `./dev.sh up` |
| Só o Postgres (p/ DBeaver) | `./dev.sh db` |
| Migrar / criar migração | `./dev.sh migrate` / `./dev.sh makemigrations` |
| Seed de usuários | `./dev.sh seed` |
| Rodar os testes | `./dev.sh test` |
| Lint + format | `./dev.sh precommit` |
| Terminal no contêiner | `./dev.sh bash` |

**Banco no DBeaver:** host `localhost`, porta **5433**, DB `cac_db`, usuário `cac_user`,
senha `cac_password`.

## Deploy

> A esteira de deploy automatizado (CI/CD em nuvem) **não faz parte deste projeto**. O
> deploy é feito de forma **manual, com o mesmo Docker** usado em desenvolvimento.

Passos de um deploy manual num servidor com Docker:

1. Clonar o repositório no servidor.
2. Criar o `.env` de produção: `DEBUG=False`, `SECRET_KEY` e `PSEUDONIMIZACAO_SALT`
   próprios e secretos, `ALLOWED_HOSTS` com o domínio, `DATABASE_URL` do banco de produção.
3. `docker compose up -d --build`.
4. `docker compose exec web python manage.py migrate`.
5. Servir os arquivos estáticos e colocar um proxy reverso (ex.: Nginx) na frente.

O **CI** (lint + testes) roda automaticamente no GitHub a cada Pull Request
(`.github/workflows/ci.yml`) — é a rede de segurança antes do merge, independente do deploy.
