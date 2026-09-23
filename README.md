# 1. Install Dependencies

set -e
pip install --no-cache-dir -r requirements.txt

# 2. Database & Static Files

python3 manage.py collectstatic --no-input
python3 manage.py migrate

# 3. Create Superuser
(Note: Create your .env file from .envexample first)

python3 manage.py createsuperuser --noinput || true

# 4. Run Application & Tunnel

Start local server
python3 manage.py runserver 5000

Expose locally to global (in a separate terminal)
lt --port 5000 --subdomain makagram --local-host 127.0.0.1
