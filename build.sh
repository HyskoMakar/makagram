#!/usr/bin/env bash
set -e

pip install --no-cache-dir -r requirements.txt

python3 manage.py collectstatic --no-input
python3 manage.py migrate
python3 manage.py createsuperuser --noinput || true