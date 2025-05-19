#!/usr/bin/env bash
set -o errexit

# Install dependencies (relative to ElectiveApp/)
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate