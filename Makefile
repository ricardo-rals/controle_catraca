.PHONY: up migrate makemigrations createsuperuser precommit test bash

up:
	docker compose up --build

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

createsuperuser:
	docker compose exec web python manage.py createsuperuser

precommit:
		docker compose exec -T web ruff check --fix .; \
		docker compose exec -T web black .; \


test:
	docker compose exec web pytest

bash:
	docker compose exec web bash

# Atalho livre: make cmd="python manage.py shell"
.PHONY: %
%:
	docker compose exec web $(cmd)