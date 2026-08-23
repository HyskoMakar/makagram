#!/usr/bin/env bash
set -euo pipefail

# Retry pip install to mitigate transient network/502 errors from PyPI
RETRIES=5
DELAY=5
for i in $(seq 1 $RETRIES); do
	if pip install --no-cache-dir -r requirements.txt; then
		break
	fi
	echo "pip install failed (attempt $i/$RETRIES). Retrying in ${DELAY}s..."
	sleep $DELAY
	if [ "$i" -eq "$RETRIES" ]; then
		echo "pip install failed after $RETRIES attempts. Exiting."
		exit 1
	fi
done

python ensure_db.py
python manage.py collectstatic --no-input
python manage.py migrate
