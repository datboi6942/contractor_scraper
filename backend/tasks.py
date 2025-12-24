import threading
import logging
from typing import Dict, Optional
from datetime import datetime

from models import JobStatus, Contractor
from database import update_job_status, add_contractor, get_job

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("JOBS")


class JobManager:
    def __init__(self):
        self.active_jobs: Dict[int, threading.Thread] = {}
        self.stop_flags: Dict[int, threading.Event] = {}

    def start_job(self, job_id: int, location: str, categories: list, thread_count: int = 3):
        if job_id in self.active_jobs and self.active_jobs[job_id].is_alive():
            logger.warning(f"[Job {job_id}] Already running, ignoring start request")
            return False

        stop_flag = threading.Event()
        self.stop_flags[job_id] = stop_flag

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, location, categories, stop_flag, thread_count),
            daemon=True
        )
        self.active_jobs[job_id] = thread
        thread.start()

        logger.info(f"[Job {job_id}] STARTED for '{location}' with {len(categories)} categories, {thread_count} threads")
        logger.info(f"[Job {job_id}] Categories: {', '.join(categories)}")
        return True

    def stop_job(self, job_id: int) -> bool:
        logger.info(f"[Job {job_id}] STOP REQUESTED")
        if job_id in self.stop_flags:
            self.stop_flags[job_id].set()
            update_job_status(job_id, status=JobStatus.CANCELLED)
            logger.info(f"[Job {job_id}] Stop flag SET - job will terminate soon")
            return True
        logger.warning(f"[Job {job_id}] No stop flag found - job may have already finished")
        return False

    def is_job_running(self, job_id: int) -> bool:
        if job_id in self.active_jobs:
            return self.active_jobs[job_id].is_alive()
        return False

    def _run_job(self, job_id: int, location: str, categories: list, stop_flag: threading.Event, thread_count: int = 3):
        # Import here to create fresh scraper instance per job
        from scraper import ContractorScraper

        total_found = 0
        scraper = None

        try:
            update_job_status(job_id, status=JobStatus.RUNNING)
            logger.info(f"[Job {job_id}] Status set to RUNNING with {thread_count} threads")

            def should_stop():
                stopped = stop_flag.is_set()
                if stopped:
                    logger.info(f"[Job {job_id}] Stop flag detected - terminating")
                return stopped

            def on_progress(category: str, current: int, total: int):
                logger.info(f"[Job {job_id}] Progress: {current}/{total} - Category: {category}")
                update_job_status(
                    job_id,
                    progress=current,
                    current_category=category,
                    total_found=total_found
                )

            def on_contractor(contractor: Contractor):
                nonlocal total_found
                result = add_contractor(contractor)
                if result:
                    total_found += 1
                    owner_info = f"Owner: {contractor.owner_name}" if contractor.owner_name else "No owner"
                    logger.info(f"[Job {job_id}] NEW #{total_found}: {contractor.name} | {owner_info} | {contractor.phone or 'No phone'}")
                    update_job_status(job_id, total_found=total_found)

            scraper = ContractorScraper(verbose=True, job_id=job_id, thread_count=thread_count)

            scraper.scrape_all_categories(
                categories=categories,
                location=location,
                progress_callback=on_progress,
                contractor_callback=on_contractor,
                should_stop=should_stop
            )

            if stop_flag.is_set():
                update_job_status(
                    job_id,
                    status=JobStatus.CANCELLED,
                    total_found=total_found
                )
                logger.info(f"[Job {job_id}] CANCELLED by user. Found {total_found} contractors before stopping.")
            else:
                update_job_status(
                    job_id,
                    status=JobStatus.COMPLETED,
                    total_found=total_found,
                    progress=len(categories)
                )
                logger.info(f"[Job {job_id}] COMPLETED successfully. Total contractors found: {total_found}")

        except Exception as e:
            logger.error(f"[Job {job_id}] FAILED with error: {e}", exc_info=True)
            update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message=str(e),
                total_found=total_found
            )

        finally:
            # Clean up browser
            if scraper:
                try:
                    scraper.cleanup()
                except:
                    pass

            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            if job_id in self.stop_flags:
                del self.stop_flags[job_id]
            logger.info(f"[Job {job_id}] Cleanup complete")


job_manager = JobManager()
