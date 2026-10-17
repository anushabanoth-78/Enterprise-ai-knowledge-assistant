import os
import uuid

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import rate_limit
from app.db import repository
from app.db.models import User
from app.models.schemas import DocumentOut, JobOut
from app.worker import celery_app, ingest_document_task

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload(file: UploadFile = File(...), user: User = Depends(rate_limit),
                 db: Session = Depends(repository.get_db)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are supported")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid PDF")

    folder = os.path.join(settings.upload_dir, str(user.id))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{uuid.uuid4().hex}.pdf")
    with open(path, "wb") as f:
        f.write(data)

    doc = repository.create_document(db, user.id, os.path.basename(file.filename), path)
    doc.task_id = ingest_document_task.delay(str(doc.id)).id
    db.commit()
    return doc


@router.get("", response_model=list[DocumentOut])
def list_docs(user: User = Depends(rate_limit), db: Session = Depends(repository.get_db)):
    return repository.list_documents(db, user.id)


@router.get("/{doc_id}/status", response_model=JobOut)
def job_status(doc_id: uuid.UUID, user: User = Depends(rate_limit), db: Session = Depends(repository.get_db)):
    doc = repository.get_document(db, user.id, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    state = AsyncResult(doc.task_id, app=celery_app).state if doc.task_id else None
    return JobOut(document_id=doc.id, status=doc.status, celery_state=state, error=doc.error)


@router.delete("/{doc_id}", status_code=204)
def delete(doc_id: uuid.UUID, user: User = Depends(rate_limit), db: Session = Depends(repository.get_db)):
    doc = repository.get_document(db, user.id, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    path = doc.path
    repository.delete_document(db, doc)
    if os.path.exists(path):
        os.remove(path)
