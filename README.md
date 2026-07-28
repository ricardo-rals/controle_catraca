# Sistema CAC — Controle de Acesso do Campus

## 📌 Descrição

O Sistema CAC — Controle de Acesso do Campus é uma aplicação desenvolvida para analisar os dados das catracas eletrônicas do IFBA. Ele permite acompanhar acessos em tempo real, gerar relatórios personalizados e consultar estatísticas de uso, oferecendo uma visão clara e organizada da movimentação no campus.

---

## 🖼️ Screenshots

### Tela de login

![Tela de login](docs/Telas/login.png)
Tela de login: Tela inicial de autenticação, onde o usuário informa suas credenciais para acessar o sistema.

### Dashboard

![Dashboard](docs/Telas/Dashboard.png)
Dashboard: visão geral dos acessos e estatísticas principais.

### Tela de Consultas

![Consultas](docs/Telas/Consultas.png)
Consultas: Histórico completo dos eventos de acesso registrados pelas catracas, com filtros e exportação.

### Tela de Importações

![Importações](docs/Telas/Importacao.png)
Tela de Importações: Interface para carregar arquivos externos (ex.: CSV) e integrar dados de acessos ao sistema.

### Tela de Relatorios

![Relatorios](docs/Telas/Relatorios.png)
Tela de Relatorios: visão geral dos acessos e estatísticas principais.

### Tela de Usuários

![Usuários](docs/Telas/Usuario.png)
Tela de Usuários: Listagem de todos os usuários cadastrados, com opções de ativar, desativar ou editar informações.

### Tela de Novo_Usuário

![Novo_Usuário](docs/Telas/Novo_Usuario.png)
Tela de Novo_Usuário: Formulário para criação de um novo usuário, incluindo dados pessoais e permissões de acesso.

### Tela de Regra de Horário

![Horário](docs/Telas/Horario.png)
Tela de Horário: Consulta detalhada dos registros de entrada e saída, filtrados por período e usuário.

---

## ⚙️ Stack


Backend: Django

Banco de dados: PostgreSQL

Infraestrutura: Docker

Testes: Pytest

Qualidade de código: Ruff + Black

---

## 🚀 Setup resumido


Para rodar o projeto em ambiente de desenvolvimento:

```bash
git clone https://github.com/SEU-USUARIO/controle-catraca.git
cd controle-catraca
cp .env.example .env
./dev.sh up
./dev.sh migrate
./dev.sh seed   # popula o banco com dados de exemplo
./dev.sh createsuperuser
```

Depois, acesse no navegador:

Aplicação: http://localhost:8000 (localhost in Bing)

Admin: http://localhost:8000/admin (localhost in Bing)

## 📚 Documentação

Toda a documentação detalhada está disponível na pasta [Parece que o resultado não era seguro para exibição. Vamos mudar as coisas e tentar outra opção!].
Inclui guias de arquitetura, fluxo de dados, e instruções avançadas de uso.

## 📚 Documentação

Toda a documentação detalhada está disponível na pasta [docs/](docs/).
Inclui guias de arquitetura, fluxo de dados e instruções avançadas de uso.

- [Arquitetura](docs/arquitetura.md)
- [Decisões técnicas](docs/decisoes.md)
- [Instalação](docs/instalacao.md)
- [LGPD e privacidade](docs/lgpd.md)
- [Schema do banco](docs/schema.md)
- [Protótipo de telas](docs/prototipo_telas_CAC.html)