"""PDF processing worker for background tasks."""

import logging
from datetime import datetime
from typing import Optional
import asyncio

from app.workers import celery_app
from app.database.storage import download_pdf, upload_csv
from app.database.jobs import get_job, update_job

logger = logging.getLogger(__name__)


def process_pdf_to_csv(pdf_data: bytes) -> bytes:
    """
    Process PDF data and convert to CSV format.

    This is a placeholder for the actual PDF processing logic.
    In production, this would contain the horse racing data extraction logic.

    Args:
        pdf_data: Binary content of the PDF file

    Returns:
        bytes: CSV data as bytes
    """
    # TODO: Implement actual PDF processing logic
    pass


@celery_app.task(bind=True, name="process_pdf")
def process_pdf(self, job_id: int):
    """
    Celery task to process a PDF file and generate CSV output.

    Args:
        job_id: ID of the job to process
    """
    logger.info(f"Starting PDF processing for job {job_id}")

    try:
        # Get job details
        job = asyncio.run(get_job(job_id))

        if not job or len(job) == 0:
            logger.error(f"Job {job_id} not found")
            raise ValueError(f"Job {job_id} not found")

        pdf_url = job.get("pdf_url")

        # Step 1: Download PDF from Supabase Storage
        logger.info(f"Downloading PDF from {pdf_url}")
        pdf_data = asyncio.run(download_pdf(pdf_url))

        # Step 2: Process PDF to CSV
        logger.info(f"Processing PDF for job {job_id}")
        csv_data = process_pdf_to_csv(pdf_data)

        # Step 3: Upload CSV to Supabase Storage
        csv_filename = f"public/job-{job_id}-{datetime.timezone.utc.strftime('%Y%m%d%H%M%S')}.csv"
        logger.info(f"Uploading CSV to {csv_filename}")
        csv_url = asyncio.run(upload_csv(csv_filename, csv_data))

        # Step 4: Update job status to completed
        logger.info(f"Updating job {job_id} status to completed")
        asyncio.run(update_job(
            job_id=job_id,
            status="completed",
            download_url=csv_url,
            completed_at=datetime.timezone.utc
        ))

        logger.info(f"Successfully completed processing job {job_id}")
        return {
            "job_id": job_id,
            "status": "completed",
            "csv_url": csv_url
        }

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)

        # Update job status to failed
        try:
            asyncio.run(update_job(
                job_id=job_id,
                status="failed",
                download_url=None,
                completed_at=datetime.timezone.utc
            ))
        except Exception as update_error:
            logger.error(f"Failed to update job status: {str(update_error)}")

        # Re-raise the exception so Celery knows the task failed
        raise
