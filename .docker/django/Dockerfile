FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/local.txt ./
RUN pip install --no-cache-dir -r local.txt

# Copy project
COPY . .

# Create start script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Waiting for database..."\n\
while ! pg_isready -h db -p 5432 -U thesis_grey_user; do\n\
    sleep 1\n\
done\n\
\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput --clear\n\
\n\
echo "Creating superuser if not exists..."\n\
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(username='\''admin'\'', email='\''admin@example.com'\'', password='\''admin123'\'') if not User.objects.filter(username='\''admin'\'').exists() else print('\''Admin user already exists'\'')" || true\n\
\n\
echo "Creating test user..."\n\
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_user(username='\''testuser'\'', email='\''test@example.com'\'', password='\''testpass123'\'') if not User.objects.filter(username='\''testuser'\'').exists() else print('\''Test user already exists'\'')" || true\n\
\n\
echo "Creating test data..."\n\
python -c "import os; import django; os.environ.setdefault('\''DJANGO_SETTINGS_MODULE'\'', '\''grey_lit_project.settings.local'\''); django.setup(); exec(open('\''minimal_test_data.py'\'').read())" || echo "Test data creation failed or already exists"\n\
\n\
echo "Starting Django development server..."\n\
python manage.py runserver 0.0.0.0:8000' > /start.sh

RUN chmod +x /start.sh

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["/start.sh"]