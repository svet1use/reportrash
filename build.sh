#!/bin/bash

echo "Building ReporTrash for Render..."

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput --settings=barangay_waste.render_settings

# Run migrations
python manage.py migrate --noinput --settings=barangay_waste.render_settings

echo "Build completed!"