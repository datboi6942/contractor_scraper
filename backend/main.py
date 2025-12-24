from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional, List
import csv
import io

from models import (
    JobCreate,
    JobResponse,
    ContractorResponse,
    PaginatedContractors,
    StatsResponse,
    ContractorCategory,
    DEFAULT_LOCATIONS,
)
from database import (
    init_database,
    create_job,
    get_job,
    get_jobs,
    delete_job,
    get_contractors,
    get_all_contractors_for_export,
    get_stats,
    get_available_locations,
    delete_contractors_by_location,
    update_job_status,
    cleanup_orphaned_jobs,
    cleanup_duplicate_contractors,
)
from tasks import job_manager
from models import JobStatus
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SERVER")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("CONTRACTOR DATA SCRAPER - Starting up...")
    logger.info("=" * 60)
    init_database()
    orphaned = cleanup_orphaned_jobs()
    if orphaned > 0:
        logger.info(f"Cleaned up {orphaned} orphaned jobs from previous session")
    # Clean up duplicate contractors on startup
    removed, updated = cleanup_duplicate_contractors()
    if removed > 0:
        logger.info(f"Cleaned up {removed} duplicate contractors ({updated} records updated)")
    logger.info("Server ready! Backend: http://localhost:8002")
    logger.info("=" * 60)
    yield
    logger.info("Server shutting down...")


app = FastAPI(
    title="Contractor Data Scraper",
    description="Web scraping framework for gathering contractor contact information",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/cleanup-duplicates")
async def cleanup_duplicates():
    """Manually trigger duplicate contractor cleanup."""
    removed, updated = cleanup_duplicate_contractors()
    return {
        "duplicates_removed": removed,
        "records_updated": updated,
        "message": f"Removed {removed} duplicates, updated {updated} records"
    }


@app.get("/api/locations")
async def get_db_locations():
    """Get all unique states and cities in the database."""
    return get_available_locations()


@app.post("/api/cleanup-location")
async def cleanup_by_location(
    keep_states: Optional[List[str]] = None,
    remove_states: Optional[List[str]] = None,
):
    """Remove contractors from specific states or keep only certain states."""
    if not keep_states and not remove_states:
        raise HTTPException(status_code=400, detail="Provide keep_states or remove_states")

    deleted = delete_contractors_by_location(
        states_to_remove=remove_states,
        keep_states=keep_states
    )
    return {"deleted": deleted, "message": f"Removed {deleted} contractors"}


@app.get("/api/stats", response_model=StatsResponse)
async def get_statistics():
    stats = get_stats()
    return StatsResponse(**stats)


@app.get("/api/config/locations")
async def get_locations():
    return [
        {"id": loc.id, "name": loc.name, "city": loc.city, "state": loc.state}
        for loc in DEFAULT_LOCATIONS
    ]


@app.get("/api/config/categories")
async def get_categories():
    return [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in ContractorCategory
    ]


@app.post("/api/jobs", response_model=JobResponse)
async def create_scraping_job(job_data: JobCreate):
    if not job_data.categories:
        raise HTTPException(status_code=400, detail="At least one category is required")

    thread_count = max(1, min(10, job_data.thread_count))  # Clamp between 1-10
    job_id = create_job(job_data.location, job_data.categories)
    job_manager.start_job(job_id, job_data.location, job_data.categories, thread_count)

    job = get_job(job_id)
    return _format_job_response(job)


@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(limit: int = Query(default=50, ge=1, le=100)):
    jobs = get_jobs(limit)
    return [_format_job_response(job) for job in jobs]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _format_job_response(job)


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] == JobStatus.RUNNING.value:
        job_manager.stop_job(job_id)
        return {"message": "Job cancelled"}
    elif job["status"] in [JobStatus.PENDING.value]:
        update_job_status(job_id, status=JobStatus.CANCELLED)
        return {"message": "Job cancelled"}
    else:
        delete_job(job_id)
        return {"message": "Job deleted"}


@app.get("/api/contractors", response_model=PaginatedContractors)
async def list_contractors(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    category: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
):
    contractors, total = get_contractors(page, per_page, category, location, search)
    total_pages = (total + per_page - 1) // per_page

    items = [
        ContractorResponse(
            id=c["id"],
            name=c["name"],
            owner_name=c.get("owner_name"),
            category=c["category"],
            address=c["address"],
            city=c["city"],
            state=c["state"],
            zip_code=c["zip_code"],
            phone=c["phone"],
            email=c["email"],
            website=c["website"],
            source=c["source"],
            location_searched=c["location_searched"],
            created_at=c["created_at"] or "",
        )
        for c in contractors
    ]

    return PaginatedContractors(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@app.get("/api/export")
async def export_contractors(
    category: Optional[str] = None,
    location: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
):
    contractors = get_all_contractors_for_export()

    # Apply filters
    if category:
        contractors = [c for c in contractors if c["category"] == category]
    if location:
        contractors = [c for c in contractors if location.lower() in c["location_searched"].lower()]
    if state:
        contractors = [c for c in contractors if c.get("state", "").upper() == state.upper()]
    if city:
        contractors = [c for c in contractors if c.get("city", "").lower() == city.lower()]

    # Generate filename based on filters
    filename_parts = ["contractors"]
    if state:
        filename_parts.append(state.upper())
    if city:
        filename_parts.append(city.replace(" ", "_"))
    if category:
        filename_parts.append(category)
    filename = "_".join(filename_parts) + ".csv"

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Name", "Owner/Contact", "Category", "Address", "City", "State", "Zip Code",
        "Phone", "Email", "Website", "Source", "Location Searched"
    ])

    for c in contractors:
        writer.writerow([
            c["name"],
            c.get("owner_name") or "",
            c["category"],
            c["address"] or "",
            c["city"] or "",
            c["state"] or "",
            c["zip_code"] or "",
            c["phone"] or "",
            c["email"] or "",
            c["website"] or "",
            c["source"],
            c["location_searched"],
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _format_job_response(job: dict) -> JobResponse:
    return JobResponse(
        id=job["id"],
        location=job["location"],
        categories=job["categories"],
        status=job["status"],
        total_found=job["total_found"],
        progress=job["progress"],
        total_categories=job["total_categories"],
        current_category=job["current_category"],
        error_message=job["error_message"],
        created_at=job["created_at"] or "",
        completed_at=job["completed_at"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
