import threading
import logging
from typing import Dict, Optional
from datetime import datetime

from models import JobStatus, Contractor
from database import (
    update_job_status,
    add_contractor,
    get_job,
    update_enrichment_job,
    update_contractor_enrichment,
    get_contractors_for_enrichment,
)
from ws_manager import manager
import asyncio

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


class EnrichmentJobManager:
    """Manages background enrichment jobs."""

    def __init__(self):
        self.active_jobs: Dict[int, threading.Thread] = {}
        self.stop_flags: Dict[int, threading.Event] = {}

    def start_enrichment_job(
        self,
        job_id: int,
        contractors: list,
        thread_count: int = 3
    ) -> bool:
        """Start an enrichment job for the given contractors."""
        if job_id in self.active_jobs and self.active_jobs[job_id].is_alive():
            logger.warning(f"[Enrich {job_id}] Already running, ignoring start request")
            return False

        stop_flag = threading.Event()
        self.stop_flags[job_id] = stop_flag

        thread = threading.Thread(
            target=self._run_enrichment,
            args=(job_id, contractors, stop_flag, thread_count),
            daemon=True
        )
        self.active_jobs[job_id] = thread
        thread.start()

        logger.info(f"[Enrich {job_id}] STARTED for {len(contractors)} contractors, {thread_count} threads")
        return True

    def stop_job(self, job_id: int) -> bool:
        """Stop an enrichment job."""
        logger.info(f"[Enrich {job_id}] STOP REQUESTED")
        if job_id in self.stop_flags:
            self.stop_flags[job_id].set()
            update_enrichment_job(job_id, status=JobStatus.CANCELLED)
            logger.info(f"[Enrich {job_id}] Stop flag SET - job will terminate soon")
            return True
        logger.warning(f"[Enrich {job_id}] No stop flag found")
        return False

    def is_job_running(self, job_id: int) -> bool:
        if job_id in self.active_jobs:
            return self.active_jobs[job_id].is_alive()
        return False

    def _run_enrichment(
        self,
        job_id: int,
        contractors: list,
        stop_flag: threading.Event,
        thread_count: int
    ):
        """Run the enrichment process."""
        from enricher import LeadEnricher

        enricher = None
        processed = 0
        enriched = 0
        failed = 0

        try:
            update_enrichment_job(job_id, status=JobStatus.RUNNING)
            logger.info(f"[Enrich {job_id}] Status set to RUNNING")

            enricher = LeadEnricher(thread_count=thread_count)

            def should_stop():
                return stop_flag.is_set()

            def on_progress(current: int, total: int):
                nonlocal processed
                processed = current
                update_enrichment_job(
                    job_id,
                    processed=processed,
                    enriched=enriched,
                    failed=failed
                )
                # Broadcast progress via WebSocket
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(manager.broadcast(job_id, {
                        "type": "progress",
                        "job_id": job_id,
                        "processed": processed,
                        "total": total,
                        "enriched": enriched,
                        "failed": failed,
                        "status": "running"
                    }))
                    loop.close()
                except Exception as e:
                    logger.error(f"WebSocket broadcast error: {e}")

            def on_result(contractor: dict, result):
                nonlocal enriched, failed

                if result.success and (result.owner_name or result.email or result.linkedin_url):
                    update_contractor_enrichment(
                        contractor_id=contractor['id'],
                        owner_name=result.owner_name,
                        email=result.email,
                        linkedin_url=result.linkedin_url,
                        confidence=result.confidence,
                        source_urls=result.source_urls  # Track where data came from
                    )
                    enriched += 1
                    sources = f" (from {len(result.source_urls)} sources)" if result.source_urls else ""
                    logger.info(f"[Enrich {job_id}] ENRICHED: {contractor['name']}{sources}")
                else:
                    failed += 1

                update_enrichment_job(
                    job_id,
                    current_business=contractor['name'],
                    enriched=enriched,
                    failed=failed
                )
                
                # Broadcast result via WebSocket
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(manager.broadcast(job_id, {
                        "type": "result",
                        "job_id": job_id,
                        "contractor": contractor['name'],
                        "success": result.success,
                        "enriched": enriched,
                        "failed": failed,
                        "processed": processed
                    }))
                    loop.close()
                except Exception as e:
                    logger.error(f"WebSocket broadcast error: {e}")

            # Set should_stop on enricher
            enricher._should_stop = should_stop

            # Run batch enrichment
            summary = enricher.enrich_batch(
                contractors=contractors,
                progress_callback=on_progress,
                result_callback=on_result
            )

            if stop_flag.is_set():
                update_enrichment_job(
                    job_id,
                    status=JobStatus.CANCELLED,
                    processed=processed,
                    enriched=enriched,
                    failed=failed
                )
                logger.info(f"[Enrich {job_id}] CANCELLED. Enriched {enriched} before stopping.")
                status = "cancelled"
            else:
                update_enrichment_job(
                    job_id,
                    status=JobStatus.COMPLETED,
                    processed=len(contractors),
                    enriched=enriched,
                    failed=failed
                )
                logger.info(f"[Enrich {job_id}] COMPLETED. Enriched: {enriched}, Failed: {failed}")
                status = "completed"

            # Broadcast final status
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(manager.broadcast(job_id, {
                    "type": "status",
                    "job_id": job_id,
                    "status": status,
                    "processed": processed,
                    "enriched": enriched,
                    "failed": failed
                }))
                loop.close()
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")

        except Exception as e:
            logger.error(f"[Enrich {job_id}] FAILED with error: {e}", exc_info=True)
            update_enrichment_job(
                job_id,
                status=JobStatus.FAILED,
                error_message=str(e),
                processed=processed,
                enriched=enriched,
                failed=failed
            )
            
            # Broadcast failure
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(manager.broadcast(job_id, {
                    "type": "status",
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                }))
                loop.close()
            except Exception as ex:
                logger.error(f"WebSocket broadcast error: {ex}")

        finally:
            if enricher:
                enricher.stop()

            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            if job_id in self.stop_flags:
                del self.stop_flags[job_id]
            logger.info(f"[Enrich {job_id}] Cleanup complete")


enrichment_manager = EnrichmentJobManager()
