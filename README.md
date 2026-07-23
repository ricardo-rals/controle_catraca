# Sistema CAC — Controle de Acesso do Campus
[![CI](https://github.com/ricardo-rals/controle_catraca/actions/workflows/ci.yml/badge.svg)](https://github.com/ricardo-rals/controle_catraca/actions/workflows/ci.yml) 
![Python](https://img.shields.io/badge/Python-3.12-blue)

## Descrição

## Links Uteis

- [Política de Pseudonimização e LGPD](docs/lgpd.md)

- [Prototipo de Telas](docs/prototipo_telas_CAC.html)

- [Arquitetura](docs/arquitetura.md)

- [Schema de Validação de CSV (Importação)](docs/schema.md)

- [Instalação e execução](docs/instalacao.md)

- [Guia de Desenvolvimento](docs/guia_de_desenvolvimento.md)

- [Decisoes de arquitetura](docs/decisoes.md)


## Screenshots


## 🛠️ Stack

### Backend
- Python 3.12
- Django 5

### Banco de Dados
- PostgreSQL

### Relatórios
- Pandas
- OpenPyXL
- WeasyPrint

### Infraestrutura
- Docker
- Docker Compose

### Documentação
- Swagger (drf-spectacular)

### CI/CD
- GitHub Actions


## Funcionalidades

## ⚙️ Setup

### Clone o repositório

```bash
git clone https://github.com/ricardo-rals/controle_catraca.git
```

### Entre na pasta

```bash
cd controle_catraca
```

### Inicie os containers

```bash
./dev.sh up
```

### Execute as migrações

```bash
./dev.sh migrate
```

### Popule o banco

```bash
./dev.sh seed
```

### Acesse o sistema
- A aplicação: http://localhost:8000
- A área administrativa: http://localhost:8000/admin

## Estrutura do Projeto


## Autores