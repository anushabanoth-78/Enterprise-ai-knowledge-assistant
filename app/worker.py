import uuid

from celery import Celery

from app.core.config import settings

celery_app = Celery("worker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1,
                       task_soft_time_limit=900, task_time_limit=1000)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60,
                 max_retries=2, name="ingest_document")
def ingest_document_task(self, doc_id: str) -> None:
    from app.services.ingestion import process_document
    process_document(uuid.UUID(doc_id))
