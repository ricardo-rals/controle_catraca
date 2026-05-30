# Sistema DAC — Controle de Acesso do Campus

Projeto Django com PostgreSQL, Docker e ferramentas de qualidade de código automatizadas para desenvolvimento colaborativo.

## Pré-requisitos
- Docker e Docker Compose instalados
- Git configurado

## Passos para configurar o ambiente

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU-USUARIO/catraca-campus.git
cd catraca-campus
```

### 2. Copiar o arquivo de variáveis de ambiente
```bash
cp .env.example .env
```

### 3. Subir os containers Docker
```bash
docker compose up --build
```

### 4. Rodar as migrações e criar o superusuário
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### 5. Instalar dependências de desenvolvimento (ruff, black, pre-commit)
```bash
docker compose exec web pip install -r requirements/dev.txt
```

### 6. Instalar e rodar o pre-commit
```bash
docker compose exec web pre-commit install
docker compose exec web pre-commit run --all-files
```

## Como usar o pre-commit
- O pre-commit verifica e formata o código automaticamente antes de cada commit.
- Se o pre-commit modificar arquivos, rode:
  ```bash
  docker compose exec web git add .
  ```
  e tente o commit novamente.

## Como fazer commits dentro do Docker
1. Abra um terminal interativo no container:
	```bash
	docker compose exec web bash
	```
2. Faça as alterações desejadas no código.
3. Adicione os arquivos:
	```bash
	git add .
	```
4. Faça o commit:
	```bash
	git commit -m "mensagem do commit"
	```
5. Envie para o repositório remoto:
	```bash
	git push
	```

> **Dica:** Sempre rode os comandos git dentro do container para garantir que o pre-commit funcione corretamente.

## Problemas comuns
- Se aparecer erro de pre-commit, rode `git add .` e tente o commit novamente.
- Se não quiser enviar algum arquivo para o repositório, adicione o nome dele no `.gitignore`.

---

Pronto! Seu ambiente estará configurado e padronizado para todo o time.

---

## Commits semânticos

Para manter o histórico do projeto organizado e facilitar a revisão, utilize o padrão de commit semântico. O formato é:

```
tipo(HU-XXX): descrição em minúsculas
```

**Tipos mais usados:**

| Tipo      | Quando usar                        | Exemplo                                              |
|-----------|------------------------------------|------------------------------------------------------|
| feat      | Nova funcionalidade                | feat(HU-010): adiciona endpoint de relatórios        |
| fix       | Correção de bug                    | fix(HU-012): corrige erro de autenticação            |
| docs      | Documentação                       | docs(HU-006): atualiza instruções no README          |
| test      | Testes                             | test(HU-056): adiciona teste para importação         |
| chore     | Organização/configuração           | chore(HU-005): adiciona ruff, black e pre-commit     |
| refactor  | Refatoração sem mudar comportamento| refactor(HU-027): simplifica lógica de validação     |
| style     | Apenas formatação                  | style(HU-023): ajusta identação e espaços            |

**Exemplo prático:**

```bash
git add .
git commit -m "feat(HU-018): adiciona parser de CSV com validação"
git push
```

> Sempre use o código do card (HU-XXX) relacionado à tarefa no commit.
