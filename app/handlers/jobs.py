"""Job endpoint handlers."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import jobs as jobs_db
from app.models import (
    JobCreate,
    JobListQueryParams,
    JobListResponse,
    JobResponse,
)
from app.workers import celery_app
from app.workers.pdf_processor import process_pdf

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(request_body: JobCreate) -> JobResponse:
    """
    Create a new job and start background processing.

    Args:
        job_data: Job creation request with title and pdf_path

    Returns:
        JobResponse: Created job details
    """
    pdf_url = request_body.pdf_url
    title = request_body.title
    job = await jobs_db.create_job(title=title, pdf_url=pdf_url)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create job"
        )

    worker = process_pdf.delay(job["id"])

    try:
        job = await jobs_db.update_job(job["id"], worker_id=worker.id)
    except Exception as e:
        logger.error(f"Failed to update job with worker ID {worker.id}: {e}")

    return JobResponse(**job)


@router.get("/jobs", status_code=status.HTTP_200_OK)
async def get_jobs(params: JobListQueryParams = Depends()) -> JobListResponse:
    """
    Get paginated list of all jobs.

    Args:
        params: Query parameters (page, limit)

    Returns:
        JobListResponse: Paginated list of jobs
    """
    limit = params.limit
    page = params.page
    jobs = await jobs_db.get_jobs(limit, page)
    return JobListResponse(data=jobs, page=page, limit=limit, next_page=len(jobs) > limit)


@router.get("/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def get_job(job_id: int) -> JobResponse:
    """
    Get a single job by ID.

    Used for both initial fetch and polling.

    Args:
        job_id: Job ID

    Returns:
        JobResponse: Job details
    """
    job = await jobs_db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse(**job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: int) -> None:
    """
    Delete a job and its associated files from storage.

    Args:
        job_id: Job ID

    Returns:
        None: 204 No Content on success
    """
    job = await jobs_db.delete_job(job_id)
    if job and job.get("worker_id"):
        celery_app.control.revoke(job["worker_id"], terminate=True)
    return None
