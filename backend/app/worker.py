from celery import Celery
from .config import settings

celery_app = Celery(
    "subtitle_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)
celery_app.conf.task_routes = {"run_job_pipeline": {"queue": "default"}}
celery_app.conf.result_expires = 3600
