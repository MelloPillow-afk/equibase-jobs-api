"""Job-related Pydantic models for request/response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """Job status enumeration."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    """Request model for creating a new job."""

    title: str = Field(..., min_length=1, max_length=255, description="Job title")
    pdf_url: str = Field(
        ...,
        min_length=1,
        description="URL to PDF file in Supabase Storage",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Process Q4 Financial Report",
                "pdf_url": "https://supabase.co/storage/uploads/financial-report-q4.pdf",
            }
        }
    )


class JobResponse(BaseModel):
    """Response model for a single job."""

    id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    status: JobStatus = Field(..., description="Current job status")
    pdf_url: str = Field(..., description="URL to source PDF in Supabase Storage")
    download_url: str | None = Field(None, description="URL to processed CSV file")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Process Q4 Financial Report",
                "status": "completed",
                "pdf_url": "https://supabase.co/storage/uploads/financial-report-q4.pdf",
                "download_url": "https://supabase.co/storage/outputs/financial-report-q4.csv",
                "created_at": "2025-01-15T10:30:00Z",
                "completed_at": "2025-01-15T10:40:00Z",
            }
        },
    )


class JobResponse(BaseModel):
    """Response model for a single job."""

    id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    status: JobStatus = Field(..., description="Current job status")
    pdf_url: str = Field(..., description="URL to source PDF in Supabase Storage")
    file_download_url: str | None = Field(None, description="URL to processed CSV file")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Process Q4 Financial Report",
                "status": "completed",
                "pdf_url": "https://supabase.co/storage/uploads/financial-report-q4.pdf",
                "download_url": "https://supabase.co/storage/outputs/financial-report-q4.csv",
                "created_at": "2025-01-15T10:30:00Z",
                "completed_at": "2025-01-15T10:40:00Z",
            }
        },
    )


class JobListQueryParams(BaseModel):
    """Query parameters for GET /jobs endpoint."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=50, description="Number of items per page (max 50)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "limit": 20,
            }
        }
    )


class JobListResponse(BaseModel):
    """Response model for paginated job list."""

    data: list[JobResponse] = Field(..., description="List of jobs")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=50, description="Items per page")
    next_page: bool = Field(..., description="Whether more pages exist")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "id": 1,
                        "title": "Process Q4 Financial Report",
                        "status": "completed",
                        "pdf_url": "https://supabase.co/storage/uploads/report.pdf",
                        "download_url": "https://supabase.co/storage/outputs/report.csv",
                        "created_at": "2025-01-15T10:30:00Z",
                        "completed_at": "2025-01-15T10:40:00Z",
                    }
                ],
                "page": 1,
                "limit": 20,
                "next_page": False,
            }
        }
    )
