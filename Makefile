SHELL:=/bin/bash
ARGS = $(filter-out $@,$(MAKECMDGOALS))
MAKEFLAGS += --silent
BASE_PATH=${PWD}
PYTHON_EXEC=python
DOCKER_COMPOSE_FILE=$(shell echo -f docker-compose.yml -f docker-compose.override.yml)
VENV_PATH=~/venv/django_template

include src/.env
export $(shell sed 's/=.*//' src/.env)
show_env:
	# Show wich DOCKER_COMPOSE_FILE and ENV the recipes will user
	# It should be referenced by all other recipes you want it to show.
	# It's only printed once even when more than a recipe executed uses it
	sh -c "if [ \"${ENV_PRINTED:-0}\" != \"1\" ]; \
	then \
		echo DOCKER_COMPOSE_FILE = \"${DOCKER_COMPOSE_FILE}\"; \
		echo OSFLAG = \"${OSFLAG}\"; \
	fi; \
	ENV_PRINTED=1;"

_cp_env_file:
	@cp -f src/.env.sample .env

_ensure_env:
	@if [ ! -f .env ]; then \
		echo "Arquivo .env não encontrado. Copiando de src/.env.sample..."; \
		cp src/.env.sample .env; \
		echo "Arquivo .env criado com sucesso."; \
	fi

init: _cp_env_file

_rebuild: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} down
	docker-compose ${DOCKER_COMPOSE_FILE} build --no-cache --force-rm

up: show_env _ensure_env
	docker-compose ${DOCKER_COMPOSE_FILE} up -d --remove-orphans

up_debug: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} stop app
	docker-compose ${DOCKER_COMPOSE_FILE} -f docker-compose.override.debug.yml up -d --remove-orphans

up_normal: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} stop app
	docker-compose ${DOCKER_COMPOSE_FILE} up -d --remove-orphans

checkcode: show_env
	echo "verify pep8 ..."
	docker-compose ${DOCKER_COMPOSE_FILE} exec app flake8 .
	docker-compose ${DOCKER_COMPOSE_FILE} exec app isort . --check-only

flake8: show_env
	echo "verify pep8 ..."
	docker-compose ${DOCKER_COMPOSE_FILE} exec app black .
	docker-compose ${DOCKER_COMPOSE_FILE} exec app isort .
	docker-compose ${DOCKER_COMPOSE_FILE} exec app flake8 .

localflake8: show_env
	echo "verify pep8 ..."
	black . && isort . && flake8 .

log: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200 app

logs: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200

stop: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} stop

status: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} ps

restart: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} restart

sh: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec ${ARGS} bash

test: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app pytest
	sudo chown -R "${USER}:${USER}" ./

psql: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec db psql -d database

pgcli: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app pgcli postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

_drop_db:
	docker-compose ${DOCKER_COMPOSE_FILE} stop db
	docker-compose ${DOCKER_COMPOSE_FILE} rm db

_create_db:
	docker-compose ${DOCKER_COMPOSE_FILE} up -d db

recreate_db: show_env _drop_db _create_db

createsuperuser: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} ./manage.py shell -c "from apps.user.models import User; User.objects.create_superuser('root@root.com.br', 'root', name='root'); print('Superuser created: root@root.com.br:root')"

everyone_superuser: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.all().update(is_staff=True, is_superuser=True); print('All users are superusers')"

fixtures: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app pytest --fixtures

migrate: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate ${ARGS}

collectstatic: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py collectstatic --no-input

makemigrations: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py makemigrations ${ARGS}
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate

migrate: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate

pip_install: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} -m pip install -r requirements.txt

manage: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py ${ARGS}

test-watch: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ptw --clear --

coverage: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app pytest --cov --cov-report xml:coverage.xml
	docker-compose ${DOCKER_COMPOSE_FILE} exec app coverage html
	sudo chown -R "${USER}:${USER}" ./src/htmlcov

clean_db: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec db psql -d ${POSTGRES_DB} -c 'drop schema public cascade; create schema public;'

showmigrations: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py showmigrations ${ARGS}

restartq: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} stop djangoq
	docker-compose ${DOCKER_COMPOSE_FILE} up -d djangoq

chown_project:
	sudo chown -R "${USER}:${USER}" ./

generate_factories_bot: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py generate_factories

generate_factories: show_env generate_factories_bot chown_project flake8

create_venv: show_env
	python3 -m venv ${VENV_PATH}
	${VENV_PATH}/bin/python -m pip install --upgrade pip setuptools wheel
	${VENV_PATH}/bin/pip install -r ./src/requirements.txt

upgrade_packages: show_env pip_install
	docker-compose ${DOCKER_COMPOSE_FILE} exec app pip-upgrade --skip-virtualenv-check

kafka_consumer: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} ./manage.py kafka_consumer

show_coverage: show_env coverage
	cd src/htmlcov && python3 -m http.server --bind 0.0.0.0 9100

# Trivy - Security Scanner (Docker)
TRIVY_IMAGE ?= aquasec/trivy:latest

security-scan:
	@echo "Executando varredura de vulnerabilidades na pasta src (Trivy Docker)..."
	docker run --rm -v $(PWD):/project -v trivy-cache:/root/.cache/trivy $(TRIVY_IMAGE) fs \
		--scanners vuln,misconfig,secret \
		--exit-code 0 \
		--severity HIGH,CRITICAL,MEDIUM \
		/project/src

security-scan-json:
	@echo "Executando varredura de vulnerabilidades (saída JSON)..."
	docker run --rm -v $(PWD):/project -v trivy-cache:/root/.cache/trivy $(TRIVY_IMAGE) fs \
		--scanners vuln,misconfig,secret \
		--exit-code 0 \
		--severity HIGH,CRITICAL,MEDIUM \
		--format json \
		-o /project/trivy-report.json \
		/project/src

security-scan-table:
	@echo "Executando varredura de vulnerabilidades (formato tabela)..."
	docker run --rm -v $(PWD):/project -v trivy-cache:/root/.cache/trivy $(TRIVY_IMAGE) fs \
		--scanners vuln,misconfig,secret \
		--exit-code 0 \
		--format table \
		/project/src

clean-trivy-cache:
	@echo "Limpando cache do Trivy..."
	docker volume rm -f trivy-cache
