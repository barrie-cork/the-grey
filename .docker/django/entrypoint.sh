#!/bin/sh

set -e

# Wait for PostgreSQL to be ready
until pg_isready -h ${DB_HOST:-db} -p ${DB_PORT:-5432} -U ${POSTGRES_USER:-thesis_grey_user}; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "PostgreSQL is ready!"

# Execute the command passed to the entrypoint
exec "$@"