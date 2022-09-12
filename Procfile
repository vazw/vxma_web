web: gunicorn app:app --workers 3 --timeout 600 --log-file - --log-level debug --timeout 90
queue: celery -A app:celery_app worker --loglevel=debug --concurrency=2
