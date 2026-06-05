#!/bin/sh

# Check if PostgreSQL is used and wait for it
if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

echo "Running migrations..."
python manage.py migrate --no-input

echo "Seeding default corporate data..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.companies.models import Company
from django.contrib.auth import get_user_model
User = get_user_model()
company, created = Company.objects.get_or_create(name='Test Company', defaults={'slug': 'test-company'})
if not User.objects.filter(email='admin@inframind.com').exists():
    User.objects.create_superuser('admin@inframind.com', 'AdminPassword123!', company=company)
    print('Superuser default created.')
"

# Run development or production server
if [ "$DEBUG" = "True" ]
then
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting Gunicorn server..."
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
