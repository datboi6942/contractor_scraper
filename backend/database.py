import sqlite3
import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager
import threading

from models import Contractor, Job, JobStatus

DATABASE_PATH = "contractors.db"
_lock = threading.Lock()
logger = logging.getLogger("DATABASE")


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Extract digits only from phone number for comparison."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    # Return last 10 digits (ignore country code)
    if len(digits) >= 10:
        return digits[-10:]
    return digits if digits else None


def normalize_name(name: Optional[str]) -> Optional[str]:
    """Normalize business name for comparison."""
    if not name:
        return None
    # Lowercase, strip whitespace, remove common suffixes
    normalized = name.lower().strip()
    # Remove common business suffixes
    for suffix in [' llc', ' inc', ' corp', ' ltd', ' co', ' company', ' services', ' service']:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    return normalized.strip()


def normalize_website(website: Optional[str]) -> Optional[str]:
    """Extract domain from website for comparison."""
    if not website:
        return None
    # Remove protocol and www
    domain = website.lower().strip()
    domain = re.sub(r'^https?://', '', domain)
    domain = re.sub(r'^www\.', '', domain)
    # Remove path
    domain = domain.split('/')[0]
    return domain if domain else None


def normalize_email(email: Optional[str]) -> Optional[str]:
    """Normalize email for comparison."""
    if not email:
        return None
    return email.lower().strip()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_name TEXT,
                category TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                source TEXT NOT NULL,
                location_searched TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: Add owner_name column if it doesn't exist
        cursor.execute("PRAGMA table_info(contractors)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'owner_name' not in columns:
            cursor.execute("ALTER TABLE contractors ADD COLUMN owner_name TEXT")
            logger.info("Added owner_name column to contractors table")

        # Migration: Remove old UNIQUE constraint by recreating table
        # Check if old constraint exists
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='contractors'")
        create_sql = cursor.fetchone()
        if create_sql and 'UNIQUE' in create_sql[0]:
            logger.info("Migrating database: removing old UNIQUE constraint...")
            cursor.execute("ALTER TABLE contractors RENAME TO contractors_old")
            cursor.execute("""
                CREATE TABLE contractors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_name TEXT,
                    category TEXT NOT NULL,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    source TEXT NOT NULL,
                    location_searched TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO contractors (id, name, owner_name, category, address, city, state, zip_code, phone, email, website, source, location_searched, created_at)
                SELECT id, name, owner_name, category, address, city, state, zip_code, phone, email, website, source, location_searched, created_at
                FROM contractors_old
            """)
            cursor.execute("DROP TABLE contractors_old")
            logger.info("Database migration complete: UNIQUE constraint removed")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                categories TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                total_found INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0,
                total_categories INTEGER DEFAULT 0,
                current_category TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contractors_category
            ON contractors(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contractors_location
            ON contractors(location_searched)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contractors_phone
            ON contractors(phone)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contractors_email
            ON contractors(email)
        """)

        conn.commit()


def find_duplicate(cursor, contractor: Contractor) -> Optional[dict]:
    """Find existing contractor that is a TRUE duplicate.

    A TRUE duplicate is:
    - Same phone number (exact match after normalization)
    - OR same email (exact match)
    - OR same website domain AND same/similar name AND no conflicting phone

    NOT a duplicate if:
    - Different phone numbers (could be different locations/contacts)
    - Different emails with different phones
    """
    norm_phone = normalize_phone(contractor.phone)
    norm_email = normalize_email(contractor.email)
    norm_website = normalize_website(contractor.website)
    norm_name = normalize_name(contractor.name)

    # PRIORITY 1: Exact phone match (strongest indicator)
    if norm_phone and len(norm_phone) >= 10:
        cursor.execute("SELECT * FROM contractors")
        for row in cursor.fetchall():
            existing = dict(row)
            existing_phone = normalize_phone(existing.get('phone'))
            if existing_phone and norm_phone == existing_phone:
                return existing

    # PRIORITY 2: Exact email match
    if norm_email:
        cursor.execute("SELECT * FROM contractors WHERE LOWER(email) = ?", (norm_email,))
        row = cursor.fetchone()
        if row:
            existing = dict(row)
            # But if phones are DIFFERENT, not a duplicate (different contact)
            existing_phone = normalize_phone(existing.get('phone'))
            if norm_phone and existing_phone and norm_phone != existing_phone:
                return None  # Different phones = different entry
            return existing

    # PRIORITY 3: Same website domain + similar name (but only if no conflicting phone)
    if norm_website and norm_name:
        cursor.execute("SELECT * FROM contractors WHERE LOWER(website) LIKE ?", (f"%{norm_website}%",))
        for row in cursor.fetchall():
            existing = dict(row)
            existing_name = normalize_name(existing.get('name'))
            existing_phone = normalize_phone(existing.get('phone'))

            # Check if names are similar
            if existing_name and (norm_name in existing_name or existing_name in norm_name):
                # If both have phones and they're different, NOT a duplicate
                if norm_phone and existing_phone and norm_phone != existing_phone:
                    continue  # Different phones = keep both
                return existing

    return None


def merge_contractor_data(existing: dict, new: Contractor) -> dict:
    """Merge new contractor data into existing, filling in missing fields."""
    updates = {}

    # Fill in missing fields from new data
    if not existing.get('owner_name') and new.owner_name:
        updates['owner_name'] = new.owner_name
    if not existing.get('address') and new.address:
        updates['address'] = new.address
    if not existing.get('city') and new.city:
        updates['city'] = new.city
    if not existing.get('state') and new.state:
        updates['state'] = new.state
    if not existing.get('zip_code') and new.zip_code:
        updates['zip_code'] = new.zip_code
    if not existing.get('phone') and new.phone:
        updates['phone'] = new.phone
    if not existing.get('email') and new.email:
        updates['email'] = new.email
    if not existing.get('website') and new.website:
        updates['website'] = new.website

    return updates


def add_contractor(contractor: Contractor) -> Optional[int]:
    """Add contractor with smart duplicate detection and merging."""
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Check for existing duplicate
            existing = find_duplicate(cursor, contractor)

            if existing:
                # Merge data into existing record
                updates = merge_contractor_data(existing, contractor)

                if updates:
                    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
                    params = list(updates.values()) + [existing['id']]
                    cursor.execute(f"UPDATE contractors SET {set_clause} WHERE id = ?", params)
                    conn.commit()
                    logger.info(f"MERGED: '{contractor.name}' into existing '{existing['name']}' (ID: {existing['id']})")
                    return None  # Return None to indicate merge, not new insert
                else:
                    logger.debug(f"DUPLICATE: '{contractor.name}' matches '{existing['name']}' - skipped")
                    return None

            # No duplicate found, insert new record
            cursor.execute("""
                INSERT INTO contractors
                (name, owner_name, category, address, city, state, zip_code, phone, email, website, source, location_searched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contractor.name,
                contractor.owner_name,
                contractor.category,
                contractor.address,
                contractor.city,
                contractor.state,
                contractor.zip_code,
                contractor.phone,
                contractor.email,
                contractor.website,
                contractor.source,
                contractor.location_searched
            ))
            conn.commit()
            return cursor.lastrowid


def get_contractors(
    page: int = 1,
    per_page: int = 50,
    category: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None
) -> Tuple[List[dict], int]:
    with get_connection() as conn:
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if category:
            where_clauses.append("category = ?")
            params.append(category)

        if location:
            where_clauses.append("location_searched LIKE ?")
            params.append(f"%{location}%")

        if search:
            where_clauses.append("(name LIKE ? OR address LIKE ? OR phone LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        cursor.execute(f"SELECT COUNT(*) FROM contractors {where_sql}", params)
        total = cursor.fetchone()[0]

        offset = (page - 1) * per_page
        cursor.execute(f"""
            SELECT * FROM contractors {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

        rows = cursor.fetchall()
        contractors = [dict(row) for row in rows]

        return contractors, total


def get_all_contractors_for_export() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contractors ORDER BY category, name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def create_job(location: str, categories: List[str]) -> int:
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (location, categories, status, total_categories)
                VALUES (?, ?, ?, ?)
            """, (location, ",".join(categories), JobStatus.PENDING.value, len(categories)))
            conn.commit()
            return cursor.lastrowid


def get_job(job_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            job = dict(row)
            job["categories"] = job["categories"].split(",")
            return job
        return None


def get_jobs(limit: int = 50) -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            job = dict(row)
            job["categories"] = job["categories"].split(",")
            jobs.append(job)
        return jobs


def update_job_status(
    job_id: int,
    status: Optional[JobStatus] = None,
    total_found: Optional[int] = None,
    progress: Optional[int] = None,
    current_category: Optional[str] = None,
    error_message: Optional[str] = None
):
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if status is not None:
                updates.append("status = ?")
                params.append(status.value)
                if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    updates.append("completed_at = ?")
                    params.append(datetime.now().isoformat())

            if total_found is not None:
                updates.append("total_found = ?")
                params.append(total_found)

            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)

            if current_category is not None:
                updates.append("current_category = ?")
                params.append(current_category)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if updates:
                params.append(job_id)
                cursor.execute(f"""
                    UPDATE jobs SET {", ".join(updates)} WHERE id = ?
                """, params)
                conn.commit()


def get_available_locations() -> dict:
    """Get all unique states and cities in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT state FROM contractors
            WHERE state IS NOT NULL AND state != ''
            ORDER BY state
        """)
        states = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT city, state FROM contractors
            WHERE city IS NOT NULL AND city != ''
            ORDER BY state, city
        """)
        cities = [{"city": row[0], "state": row[1]} for row in cursor.fetchall()]

        return {"states": states, "cities": cities}


def delete_contractors_by_location(states_to_remove: list = None, keep_states: list = None) -> int:
    """Delete contractors from specific states or keep only certain states."""
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()

            if states_to_remove:
                placeholders = ",".join("?" * len(states_to_remove))
                cursor.execute(
                    f"DELETE FROM contractors WHERE UPPER(state) IN ({placeholders})",
                    [s.upper() for s in states_to_remove]
                )
            elif keep_states:
                placeholders = ",".join("?" * len(keep_states))
                cursor.execute(
                    f"DELETE FROM contractors WHERE UPPER(state) NOT IN ({placeholders}) OR state IS NULL",
                    [s.upper() for s in keep_states]
                )

            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Deleted {deleted} contractors by location filter")
            return deleted


def get_stats() -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM contractors")
        total_contractors = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM contractors WHERE owner_name IS NOT NULL AND owner_name != ''")
        with_owner = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM contractors WHERE phone IS NOT NULL AND phone != ''")
        with_phone = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM contractors WHERE email IS NOT NULL AND email != ''")
        with_email = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = ?", (JobStatus.RUNNING.value,))
        active_jobs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT category, COUNT(*) as count FROM contractors GROUP BY category
        """)
        categories = {row["category"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_contractors": total_contractors,
            "with_owner": with_owner,
            "with_phone": with_phone,
            "with_email": with_email,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "categories_breakdown": categories
        }


def delete_job(job_id: int) -> bool:
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0


def cleanup_orphaned_jobs() -> int:
    """Mark any 'running' or 'pending' jobs as 'failed' on startup.
    These are orphaned jobs from a previous server crash."""
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs
                SET status = ?, error_message = 'Server restarted - job was interrupted'
                WHERE status IN (?, ?)
            """, (JobStatus.FAILED.value, JobStatus.RUNNING.value, JobStatus.PENDING.value))
            conn.commit()
            return cursor.rowcount


def cleanup_duplicate_contractors() -> Tuple[int, int]:
    """Scan database and merge TRUE duplicate contractors.

    TRUE duplicates (merge these):
    - Same phone number = same business

    NOT duplicates (keep separate):
    - Different phone numbers = possibly different locations/contacts
    - Same name but different phones = keep both

    Returns (duplicates_removed, records_updated).
    """
    with _lock:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get all contractors ordered by ID (keep oldest)
            cursor.execute("SELECT * FROM contractors ORDER BY id ASC")
            all_contractors = [dict(row) for row in cursor.fetchall()]

            if not all_contractors:
                return 0, 0

            # Group by normalized phone (strongest duplicate indicator)
            phone_groups = {}  # normalized_phone -> list of contractor dicts
            no_phone = []  # contractors without phone

            for c in all_contractors:
                norm_phone = normalize_phone(c.get('phone'))
                if norm_phone and len(norm_phone) >= 10:
                    if norm_phone not in phone_groups:
                        phone_groups[norm_phone] = []
                    phone_groups[norm_phone].append(c)
                else:
                    no_phone.append(c)

            to_delete = []
            updates_made = 0

            # Merge contractors with same phone number
            for norm_phone, group in phone_groups.items():
                if len(group) <= 1:
                    continue

                # Keep the first (oldest) entry, merge others into it
                primary = group[0]
                primary_id = primary['id']

                for duplicate in group[1:]:
                    dup_id = duplicate['id']

                    # Merge missing fields into primary
                    updates = {}
                    for field in ['owner_name', 'address', 'city', 'state', 'zip_code', 'email', 'website']:
                        if not primary.get(field) and duplicate.get(field):
                            updates[field] = duplicate[field]
                            primary[field] = duplicate[field]  # Update local copy too

                    if updates:
                        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
                        params = list(updates.values()) + [primary_id]
                        cursor.execute(f"UPDATE contractors SET {set_clause} WHERE id = ?", params)
                        updates_made += 1

                    to_delete.append(dup_id)
                    logger.info(f"CLEANUP: Merging '{duplicate['name']}' (ID:{dup_id}) into '{primary['name']}' (ID:{primary_id}) [same phone]")

            # For entries without phone, check for email duplicates
            email_groups = {}
            for c in no_phone:
                if c['id'] in to_delete:
                    continue
                norm_email = normalize_email(c.get('email'))
                if norm_email:
                    if norm_email not in email_groups:
                        email_groups[norm_email] = []
                    email_groups[norm_email].append(c)

            for norm_email, group in email_groups.items():
                if len(group) <= 1:
                    continue

                primary = group[0]
                primary_id = primary['id']

                for duplicate in group[1:]:
                    dup_id = duplicate['id']

                    updates = {}
                    for field in ['owner_name', 'address', 'city', 'state', 'zip_code', 'phone', 'website']:
                        if not primary.get(field) and duplicate.get(field):
                            updates[field] = duplicate[field]
                            primary[field] = duplicate[field]

                    if updates:
                        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
                        params = list(updates.values()) + [primary_id]
                        cursor.execute(f"UPDATE contractors SET {set_clause} WHERE id = ?", params)
                        updates_made += 1

                    to_delete.append(dup_id)
                    logger.info(f"CLEANUP: Merging '{duplicate['name']}' (ID:{dup_id}) into '{primary['name']}' (ID:{primary_id}) [same email]")

            # Delete duplicates
            if to_delete:
                placeholders = ",".join("?" * len(to_delete))
                cursor.execute(f"DELETE FROM contractors WHERE id IN ({placeholders})", to_delete)

            conn.commit()

            if to_delete:
                logger.info(f"CLEANUP COMPLETE: Removed {len(to_delete)} duplicates, updated {updates_made} records")
            return len(to_delete), updates_made
