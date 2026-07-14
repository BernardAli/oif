#!/usr/bin/env bash
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-$HOME/oif_project_final}"
cd "$PROJECT_HOME"

python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy

printf '\nDeployment preparation complete. Reload the web app from the PythonAnywhere Web tab.\n'
