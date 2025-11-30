### Components

1. **Frontend**: React (Vercel)
2. **Backend**: FastAPI (Render - single web service)
3. **Storage**: Supabase Storage (PDFs + CSVs)
4. **Database**: Supabase Postgres (Job records)

### Architecture Flow

```
1. User uploads PDF via React
   ↓
2. React uploads PDF to Supabase Storage
   ↓
3. React calls FastAPI POST /process
   ↓
4. FastAPI:
   - Creates job record in Supabase DB (status="processing")
   - Returns job_id immediately
   - Starts background task in same process
   ↓
5. Background task:
   - Downloads PDF from Supabase Storage
   - Processes PDF → CSV (10 mins)
   - Uploads CSV to Supabase Storage
   - Updates job in Supabase DB (status="completed", download_url)
   ↓
6. React polls GET /status/{job_id} every 3s
   - Queries Supabase DB for job status
   ↓
7. When completed, user downloads CSV from Supabase Storage
```

### Polling Strategy

```
Dashboard shows list of all jobs
  ↓
Frontend identifies the single "processing" job
  ↓
Polls ONLY that job's status every 3s
  ↓
When status changes to "completed"/"failed":
  - Stop polling
  - Update UI
  - If new job is queued, start polling that one
```

### Data Tables

```
	Job Table:
	- id (uuid, primary key)
	- title (text)
	- status (text: "processing" | "completed" | "failed")
	- download_url (text, nullable)
	- created_at (timestamp)
	- completed_at (timestamp, nullable)
```

### API Endpoints

```
POST /jobs
Body: { pdf_path: string }
Returns: { job_id: string }
Creates job, starts background processing

GET /jobs
Query: ?page=1&limit=20
Returns: { data: Job[], page: int, has_next_page: bool }
Dashboard list

GET /jobs/{job_id}
Returns: Job
Used for both: initial fetch AND polling

DELETE /jobs/{job_id} (optional)
Deletes job record + files from storage
```


### Project Structure

```
horse-race/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment variables & settings
│   ├── models/              # Pydantic models
│   ├── handlers/            # API route handlers (business logic here)
│   ├── database/            # Supabase client & operations
│   └── workers/             # Background task workers (Celery)
├── tests/
│   ├── factories/
│   ├── integration/
├── requirements.txt
└── .env.example

```

For example: 
app/handlers/jobs.py - Contains endpoint logic + orchestration
app/database/jobs.py - Contains functions like insert_job(), get_job_by_id(), update_job_status(), etc.
app/database/storage.py - Contains upload_pdf(), download_pdf(), upload_csv(), etc.


python version: 3.13.5

Setup dependencies:
fastapi - web framework
uvicorn - ASGI server
pydantic & pydantic-settings - validation
supabase - Supabase Python client
pytest & httpx - testing
celery

---

## Implementation Checklist

### Phase 1: Project Scaffold [✅]

### Phase 2: Database Layer
- [x] Create app/database/client.py (Supabase client singleton)
- [x] Create app/database/jobs.py (insert_job, get_job_by_id, update_job_status, list_jobs, delete_job)
- [ ] Create app/database/storage.py (upload_pdf, download_pdf, upload_csv, delete_file)

### Phase 3: Models & Validation
- [ ] Create app/models/job.py (JobCreate, JobResponse, JobListResponse, JobStatus enum)

### Phase 4: API Endpoints
- [ ] Implement POST /jobs handler (create job, trigger background task)
- [ ] Implement GET /jobs handler (paginated list with ?page=1&limit=20)
- [ ] Implement GET /jobs/{job_id} handler (single job status)
- [ ] Implement DELETE /jobs/{job_id} handler (cleanup job + files)
- [ ] Add CORS middleware for React frontend

### Phase 5: Background Workers
- [ ] Setup Celery configuration (broker, backend)
- [ ] Create app/workers/pdf_processor.py (Celery task)
- [ ] Implement PDF download → processing → CSV upload → status update flow
- [ ] Add error handling and logging for worker tasks

### Phase 6: Testing
- [ ] Create test factories in tests/factories/
- [ ] Write integration tests for POST /jobs
- [ ] Write integration tests for GET /jobs (pagination)
- [ ] Write integration tests for GET /jobs/{job_id}
- [ ] Write integration tests for DELETE /jobs/{job_id}
- [ ] Test background worker execution

### Phase 7: Deployment Prep
- [ ] Add health check endpoint GET /health
- [ ] Setup logging configuration
- [ ] Create deployment documentation
- [ ] Test full flow end-to-end