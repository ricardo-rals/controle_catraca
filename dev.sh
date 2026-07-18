#!/bin/bash

case "$1" in
    up)
        docker compose up --build
        ;;
    migrate)
        docker compose exec web python manage.py migrate
        ;;
    makemigrations)
        docker compose exec web python manage.py makemigrations
        ;;
    createsuperuser)
        docker compose exec web python manage.py createsuperuser
        ;;
    seed)
        docker compose exec web python manage.py seed_usuarios
        ;;
    precommit)
            docker compose exec -T web ruff check --fix .
            docker compose exec -T web black .
      
        ;;
    test)
        docker compose exec web pytest
        ;;
    bash)
        docker compose exec web bash
        ;;
    exec)
        shift
        docker compose exec web "$@"
        ;;
    *)
        echo "Uso:"
        echo "  ./dev.sh up                 sobe o projeto"
        echo "  ./dev.sh migrate            roda as migracoes"
        echo "  ./dev.sh makemigrations     cria novas migracoes"
        echo "  ./dev.sh createsuperuser    cria um superusuario"
        echo "  ./dev.sh seed               cria usuarios admin e gestor de dev"
        echo "  ./dev.sh precommit          roda o pre-commit"
        echo "  ./dev.sh test               roda os testes"
        echo "  ./dev.sh bash               abre terminal no container"
        echo "  ./dev.sh exec <comando>     roda um comando livre"
        exit 1
        ;;
esac