#!/bin/sh

echo "setup of kafka"
python manage.py kafka_setup

echo "Runnning Database Migrations..."
yes | python manage.py migrate

echo "Setting up Helper schedules..."
yes | python manage.py setup_helper_schedules

echo "Runnning Create Cache Table..."
yes | python manage.py createcachetable

echo "Runnning CollectStatic..."
yes | python manage.py collectstatic --no-input

echo "starting $@"
exec "$@"
