#!/usr/bin/env bash
# exit on error
set -o errexit

# Install the packages listed in your requirements.txt
pip install -r requirements.txt

# Collect all CSS, JS, and Images for the live server
python manage.py collectstatic --no-input

# Run any pending database updates
python manage.py migrate