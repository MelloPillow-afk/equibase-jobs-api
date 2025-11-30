"""Supabase Storage operations for PDFs and CSVs."""

import httpx
from app.database.client import database_session

BUCKET_NAME = "horse-racing-files"
EXPIRATION_TIME = 60 * 60 * 24 * 3  # 3 days

async def upload_pdf(file_path: str, file_data: bytes) -> str:
    """
    Upload a PDF file to Supabase Storage.

    Args:
        file_path: Path where file will be stored in the bucket (e.g., "pdfs/race-123.pdf")
        file_data: Binary content of the PDF file

    Returns:
        str: Public URL of the uploaded file
    """
    async with database_session() as supabase:
        response = await supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )

        # Get public URL for the uploaded file
        public_url = supabase.storage.from_(BUCKET_NAME).create_signed_url(file_path, EXPIRATION_TIME)
        return public_url


async def download_pdf(pdf_url: str) -> bytes:
    """
    Download a PDF file from a URL (typically Supabase Storage signed URL).

    Args:
        pdf_url: Complete URL to the PDF file (e.g., signed URL from Supabase Storage)

    Returns:
        bytes: Binary content of the PDF file
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(pdf_url)
        response.raise_for_status()
        return response.content


async def upload_csv(file_path: str, file_data: bytes) -> str:
    """
    Upload a CSV file to Supabase Storage.

    Args:
        file_path: Path where file will be stored in the bucket (e.g., "csvs/race-123.csv")
        file_data: Binary content of the CSV file

    Returns:
        str: Public URL of the uploaded file
    """
    async with database_session() as supabase:
        response = await supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_data,
            file_options={"content-type": "text/csv"}
        )

        # Get public URL for the uploaded file
        public_url = await supabase.storage.from_(BUCKET_NAME).create_signed_url(file_path, EXPIRATION_TIME)
        return public_url["signedURL"]


async def delete_file(file_path: str) -> None:
    """
    Delete a file from Supabase Storage.

    Args:
        file_path: Path to the file in the bucket (e.g., "pdfs/race-123.pdf")
    """
    async with database_session() as supabase:
        await supabase.storage.from_(BUCKET_NAME).remove([file_path])
