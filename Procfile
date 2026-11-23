web: python -m flask --app app db upgrade && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2
release: python -m flask --app app db upgrade
