from datetime import datetime
from app.database.client import database_session

async def get_jobs(limit: int = 50, page: int = 1):
    async with database_session() as supabase:
        response = (
            await supabase.from_("polling_jobs")
            .select("*")
            .limit(limit + 1)
            .offset((page - 1) * limit)
            .execute()
        )
        return response.data


async def get_job(job_id: int):
    async with database_session() as supabase:
        response = await supabase.from_("polling_jobs").select("*").eq("id", job_id).execute()
        return response.data


async def create_job(pdf_url: str, title: str):
    async with database_session() as supabase:
        response = (
            await supabase.from_("polling_jobs")
            .insert({"pdf_url": pdf_url, "status": "processing", "title": title})
            .execute()
        )
        return response.data[0]


async def update_job(job_id: int, status: str, download_url: str, completed_at: datetime):
    updates = {}
    if status:
        updates["status"] = status
    if download_url:
        updates["download_url"] = download_url
    if completed_at:
        updates["completed_at"] = completed_at

    async with database_session() as supabase:
        response = await supabase.from_("polling_jobs").update(updates).eq("id", job_id).execute()
        return response.data


async def delete_job(job_id: int):
    async with database_session() as supabase:
        response = await supabase.from_("polling_jobs").delete().eq("id", job_id).execute()
        return response.data
