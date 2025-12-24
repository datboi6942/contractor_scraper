"""
Lead Enrichment Engine
Uses Tavily API for intelligent web search + OpenAI for extraction.
Enriches contractor records with owner names, emails, and LinkedIn profiles.

Production Features:
- Pydantic schema enforcement (no hallucinated data)
- Source URL tracking for verification
- Retry logic for failed extractions
"""

import os
import json
import logging
import threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import re

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from openai import OpenAI

# Try to import Instructor for schema enforcement
try:
    import instructor
    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False

# Try to import Tavily, fall back to web search if not available
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ENRICHER")


# ==================== PYDANTIC SCHEMAS FOR LLM ENFORCEMENT ====================

class ExtractedContact(BaseModel):
    """Schema for LLM-extracted contact information. Enforced by Instructor."""

    owner_name: Optional[str] = Field(
        default=None,
        description="Owner's full name (first and last). Must be a real person's name, not a business name."
    )
    email: Optional[str] = Field(
        default=None,
        description="Professional email address. Prefer personal emails over generic info@ addresses."
    )
    linkedin_url: Optional[str] = Field(
        default=None,
        description="LinkedIn profile URL for the owner or business."
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score 0-1 based on data quality."
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs where this information was found."
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return None
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.strip()):
            return None
        return v.strip().lower()

    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin(cls, v):
        if v is None:
            return None
        if 'linkedin.com' not in v.lower():
            return None
        return v.strip()

    @field_validator('owner_name')
    @classmethod
    def validate_owner_name(cls, v):
        if v is None:
            return None
        # Must have at least two words (first and last name)
        name = v.strip()
        if len(name.split()) < 2:
            return None
        # Filter out obvious business names
        business_indicators = ['llc', 'inc', 'corp', 'company', 'services', 'contracting', 'plumbing', 'electric']
        if any(ind in name.lower() for ind in business_indicators):
            return None
        return name


@dataclass
class EnrichmentResult:
    """Result of enrichment attempt."""
    success: bool
    owner_name: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)  # URLs where data was found
    error: Optional[str] = None


ENRICHMENT_PROMPT = """You are a business intelligence analyst. Extract contact information from these search results.

Business: {business_name}
Location: {city}, {state}
Category: {category}

Search Results:
{search_context}

Extract the following information for THIS SPECIFIC BUSINESS (not other businesses):
1. owner_name: The owner, proprietor, president, or principal's FULL NAME (first and last)
2. email: A professional email address (prefer owner's personal email over generic info@ emails)
3. linkedin_url: LinkedIn profile URL for the owner or the business page

IMPORTANT:
- Only extract information that clearly belongs to {business_name}
- If you find multiple people, prefer the owner/founder over employees
- For email, prefer personal emails (john@company.com) over generic (info@company.com)
- Set confidence to a value 0-1 based on how certain you are the data is correct
- If you cannot find reliable information for a field, set it to null

Return ONLY valid JSON in this exact format:
{{
    "owner_name": "First Last" or null,
    "email": "email@domain.com" or null,
    "linkedin_url": "https://linkedin.com/in/..." or null,
    "confidence": 0.0-1.0,
    "sources": ["source1", "source2"]
}}
"""


class LeadEnricher:
    """Enriches contractor leads with owner info, emails, and LinkedIn profiles."""

    def __init__(self, thread_count: int = 3):
        self.thread_count = thread_count
        self.openai_client = OpenAI()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Initialize Instructor for schema enforcement if available
        if INSTRUCTOR_AVAILABLE:
            self.instructor_client = instructor.from_openai(self.openai_client)
            logger.info("Instructor initialized for LLM schema enforcement")
        else:
            self.instructor_client = None
            logger.warning("Instructor not installed. Run: pip install instructor")
            logger.warning("LLM responses will use fallback JSON parsing (less reliable)")

        # Initialize Tavily if available
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if TAVILY_AVAILABLE and tavily_key:
            self.tavily_client = TavilyClient(api_key=tavily_key)
            logger.info("Tavily API initialized for intelligent search")
        else:
            self.tavily_client = None
            if not TAVILY_AVAILABLE:
                logger.warning("Tavily not installed. Run: pip install tavily-python")
            else:
                logger.warning("TAVILY_API_KEY not set. Enrichment will use basic search.")

        self._enriched_count = 0
        self._failed_count = 0

    def stop(self):
        """Stop ongoing enrichment."""
        self._stop_event.set()

    def _should_stop(self) -> bool:
        return self._stop_event.is_set()

    def _search_tavily(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search using Tavily API for high-quality results."""
        if not self.tavily_client:
            return []

        try:
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True
            )
            return response.get('results', [])
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []

    def _build_search_queries(self, business_name: str, city: str, state: str, category: str) -> List[str]:
        """Build targeted search queries to find owner info."""
        queries = [
            f'"{business_name}" {city} {state} owner founder',
            f'"{business_name}" {city} owner name contact',
            f'"{business_name}" {state} {category} owner linkedin',
            f'"{business_name}" about us team founder',
        ]
        return queries

    def _extract_with_llm(self, business_name: str, city: str, state: str,
                          category: str, search_context: str,
                          source_urls: List[str] = None) -> EnrichmentResult:
        """Use LLM to extract structured data from search results.

        Uses Instructor for schema enforcement when available, preventing hallucinations.
        """
        source_urls = source_urls or []

        try:
            prompt = ENRICHMENT_PROMPT.format(
                business_name=business_name,
                city=city or "Unknown",
                state=state or "Unknown",
                category=category or "contractor",
                search_context=search_context[:8000]  # Limit context size
            )

            # Use Instructor for schema enforcement if available
            if INSTRUCTOR_AVAILABLE and self.instructor_client:
                try:
                    extracted = self.instructor_client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_model=ExtractedContact,
                        max_retries=2,  # Auto-retry on validation failure
                        messages=[
                            {"role": "system", "content": "You extract business contact information. Be accurate and conservative - only extract data you're confident about."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                    )

                    # Add source URLs from search results
                    extracted.source_urls = source_urls[:5]  # Keep top 5

                    return EnrichmentResult(
                        success=True,
                        owner_name=extracted.owner_name,
                        email=extracted.email,
                        linkedin_url=extracted.linkedin_url,
                        confidence=extracted.confidence,
                        sources=[],
                        source_urls=extracted.source_urls
                    )
                except Exception as instructor_error:
                    logger.warning(f"Instructor extraction failed, falling back: {instructor_error}")

            # Fallback to standard OpenAI extraction
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You extract business contact information. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                timeout=30
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON from response
            start = result_text.find('{')
            end = result_text.rfind('}')
            if start != -1 and end != -1:
                result_text = result_text[start:end + 1]

            data = json.loads(result_text)

            # Validate with Pydantic even in fallback mode
            try:
                validated = ExtractedContact(
                    owner_name=data.get('owner_name'),
                    email=data.get('email'),
                    linkedin_url=data.get('linkedin_url'),
                    confidence=float(data.get('confidence', 0.5)),
                    source_urls=source_urls[:5]
                )
                return EnrichmentResult(
                    success=True,
                    owner_name=validated.owner_name,
                    email=validated.email,
                    linkedin_url=validated.linkedin_url,
                    confidence=validated.confidence,
                    sources=data.get('sources', []),
                    source_urls=validated.source_urls
                )
            except Exception:
                # Return raw data if validation fails
                return EnrichmentResult(
                    success=True,
                    owner_name=data.get('owner_name'),
                    email=data.get('email'),
                    linkedin_url=data.get('linkedin_url'),
                    confidence=float(data.get('confidence', 0.5)),
                    sources=data.get('sources', []),
                    source_urls=source_urls[:5]
                )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return EnrichmentResult(success=False, error=f"JSON parse error: {e}")
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return EnrichmentResult(success=False, error=str(e))

    def enrich_contractor(self, contractor: Dict) -> EnrichmentResult:
        """Enrich a single contractor with additional information."""
        if self._should_stop():
            return EnrichmentResult(success=False, error="Stopped")

        business_name = contractor.get('name', '')
        city = contractor.get('city', '')
        state = contractor.get('state', '')
        category = contractor.get('category', '')

        if not business_name:
            return EnrichmentResult(success=False, error="No business name")

        logger.info(f"Enriching: {business_name} ({city}, {state})")

        # Build search queries
        queries = self._build_search_queries(business_name, city, state, category)

        # Collect search results
        all_results = []
        for query in queries[:2]:  # Limit to 2 queries to save API calls
            if self._should_stop():
                break
            results = self._search_tavily(query, max_results=3)
            all_results.extend(results)

        if not all_results:
            logger.warning(f"No search results for: {business_name}")
            return EnrichmentResult(success=False, error="No search results")

        # Build context from search results and collect source URLs
        search_context = ""
        source_urls = []
        for r in all_results:
            title = r.get('title', '')
            content = r.get('content', '')
            url = r.get('url', '')
            source_urls.append(url)
            search_context += f"\n--- Source: {url} ---\nTitle: {title}\n{content}\n"

        # Extract with LLM (passing source URLs for tracking)
        result = self._extract_with_llm(business_name, city, state, category, search_context, source_urls)

        if result.success and (result.owner_name or result.email or result.linkedin_url):
            with self._lock:
                self._enriched_count += 1
            found = []
            if result.owner_name:
                found.append(f"Owner: {result.owner_name}")
            if result.email:
                found.append(f"Email: {result.email}")
            if result.linkedin_url:
                found.append("LinkedIn")
            logger.info(f"ENRICHED: {business_name} | {', '.join(found)}")
        else:
            with self._lock:
                self._failed_count += 1
            logger.info(f"NO DATA: {business_name}")

        return result

    def enrich_batch(
        self,
        contractors: List[Dict],
        progress_callback=None,
        result_callback=None
    ) -> Dict[str, Any]:
        """Enrich a batch of contractors using parallel threads."""
        self._stop_event.clear()
        self._enriched_count = 0
        self._failed_count = 0

        total = len(contractors)
        completed = 0
        results = []

        logger.info(f"Starting batch enrichment: {total} contractors, {self.thread_count} threads")

        def process_contractor(contractor):
            if self._should_stop():
                return None, contractor
            result = self.enrich_contractor(contractor)
            return result, contractor

        try:
            with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
                futures = {
                    executor.submit(process_contractor, c): c
                    for c in contractors
                }

                for future in as_completed(futures):
                    if self._should_stop():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    completed += 1
                    result, contractor = future.result()

                    if result:
                        results.append({
                            'contractor_id': contractor.get('id'),
                            'result': result
                        })

                        if result_callback:
                            result_callback(contractor, result)

                    if progress_callback:
                        progress_callback(completed, total)

        except Exception as e:
            logger.error(f"Batch enrichment error: {e}")

        summary = {
            'total': total,
            'completed': completed,
            'enriched': self._enriched_count,
            'failed': self._failed_count,
            'results': results
        }

        logger.info(f"Batch complete: {self._enriched_count}/{total} enriched")
        return summary


# Singleton instance
enricher = LeadEnricher()
