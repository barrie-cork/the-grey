#!/bin/sh

set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the development server
echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000