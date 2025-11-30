# Horse Race API

A FastAPI service that processes horse racing PDFs and converts them to CSV format using background job processing.

## Description

This API accepts PDF uploads, processes them asynchronously, and returns downloadable CSV files. Users can track job progress through real-time status polling.

## Stack Overview

- **Backend**: FastAPI + Uvicorn
- **Database**: Supabase Postgres (job records)
- **Storage**: Supabase Storage (PDFs + CSVs)
- **Background Processing**: Celery + Redis
- **Package Management**: uv
- **Deployment**: Render

## How to Run

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Redis (for Celery)
- Supabase account

### Setup

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. **Start Redis** (if running locally)
   ```bash
   redis-server
   ```

4. **Run the API server**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. **Run the Celery worker** (in a separate terminal)
   ```bash
   uv run celery -A app.workers worker --loglevel=info
   ```

6. **Access the API**
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## API Endpoints

```
POST   /jobs              Create new job & start processing
GET    /jobs              List all jobs (paginated)
GET    /jobs/{job_id}     Get job status & download URL
DELETE /jobs/{job_id}     Delete job & associated files
```

## Architecture Flow

```
1. Frontend uploads PDF to Supabase Storage
2. Frontend calls POST /jobs with PDF path
3. API creates job record (status="processing")
4. Celery worker downloads PDF, processes it, uploads CSV
5. Worker updates job status to "completed"
6. Frontend polls GET /jobs/{job_id} for status
7. User downloads CSV from Supabase Storage
```
