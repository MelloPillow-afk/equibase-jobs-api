from datetime import datetime

from app.database.client import database_session


async def get_jobs(limit: int = 50, page: int = 1):
    async with database_session() as supabase:
        response = (
            await supabase.table("jobs")
            .select("*")
            .limit(limit + 1)
            .offset((page - 1) * limit)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data
        return []


async def get_job(job_id: int):
    async with database_session() as supabase:
        response = await supabase.table("jobs").select("*").eq("id", job_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None


async def create_job(title: str, pdf_url: str):
    async with database_session() as supabase:
        response = (
            await supabase.table("jobs")
            .insert({"pdf_url": pdf_url, "status": "processing", "title": title})
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None


async def update_job(
    job_id: int,
    *,
    status: str = None,
    download_url: str = None,
    completed_at: datetime = None,
    worker_id: str = None,
):
    updates = {}
    if status:
        updates["status"] = status
    if download_url:
        updates["file_download_url"] = download_url
    if completed_at:
        # Convert datetime to ISO format string for JSON serialization
        updates["completed_at"] = completed_at.isoformat()
    if worker_id:
        updates["worker_id"] = worker_id

    async with database_session() as supabase:
        # Pass the dictionary directly - Supabase client handles JSON serialization
        response = await supabase.table("jobs").update(updates).eq("id", job_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None


async def delete_job(job_id: int):
    async with database_session() as supabase:
        response = await supabase.table("jobs").delete().eq("id", job_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
