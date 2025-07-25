# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements/ /app/requirements/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements/local.txt

# Copy project files
COPY . /app/

# Copy entrypoint scripts and make them executable
RUN cp /app/.docker/django/entrypoint.sh /entrypoint.sh && \
    cp /app/.docker/django/start.sh /start.sh && \
    chmod +x /entrypoint.sh /start.sh

# Create static and media directories
RUN mkdir -p /app/static /app/media

# Run collectstatic (will be overridden in development)
# RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (will be overridden by docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "grey_lit_project.wsgi:application"]