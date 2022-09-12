web: gunicorn app:app --workers 3
queue: celery -A app:celery_app worker --loglevel=INFO --concurrency=2
