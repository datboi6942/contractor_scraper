import os
import json
import time
import random
import logging
import re
from typing import List, Optional, Callable, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from openai import OpenAI
import threading
from urllib.parse import urlparse, urljoin

from models import Contractor, CATEGORY_SEARCH_TERMS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

PAGE_TIMEOUT = 12000  # 12 seconds
WEBSITE_TIMEOUT = 10000  # 10 seconds for individual business sites

# Domains to skip (not useful for contact info)
SKIP_DOMAINS = {
    'google.com', 'bing.com', 'yahoo.com', 'facebook.com', 'twitter.com',
    'instagram.com', 'linkedin.com', 'youtube.com', 'yelp.com', 'yellowpages.com',
    'bbb.org', 'angieslist.com', 'homeadvisor.com', 'thumbtack.com', 'nextdoor.com',
    'mapquest.com', 'apple.com', 'pinterest.com', 'reddit.com', 'wikipedia.org',
    'amazon.com', 'craigslist.org'
}

DISCOVER_PROMPT = """Extract business website URLs from this Google search results page.

Look for URLs that appear to be actual business websites (not directories like Yelp, Yellow Pages, etc).

Return a JSON array of objects with:
- url: the business website URL
- name: business name if visible

Only include URLs that look like real business websites. Skip social media, directories, and aggregator sites.

Search results text:
{content}

JSON array:"""

EXTRACT_PROMPT = """Extract contact information from this business website.

CRITICAL LOCATION REQUIREMENT:
The business MUST be physically located in or very near: {location}
- Check the address, city, state, and zip code on the website
- If the business is in a DIFFERENT state or city far from {location}, return {{"skip": true, "reason": "wrong location"}}
- Only include businesses within ~50 miles of {location}
- National chains with no local address should be skipped

Extract ONLY if the business is in the correct location:
- name: Business name
- owner_name: Owner/proprietor's FULL NAME (first and last). Look for:
  * "Owner:", "Proprietor:", "President:", "CEO:", "Founded by", "Owned by"
  * "About Us" sections with personal introductions like "Hi, I'm [Name]" or "My name is [Name]"
  * "Meet the Team" or "Our Team" sections (look for titles like Owner, Founder, President)
  * Email signatures or contact sections with personal names
  * License holder names (e.g., "Licensed contractor: John Smith")
  * ONLY extract if you find an actual person's name, not the business name
- address: Full street address (must be near {location})
- city: City (must match or be very close to {location})
- state: State abbreviation (must match {location}'s state)
- zip_code: ZIP code
- phone: Phone number (format: (XXX) XXX-XXXX)
- email: Email address
- website: This website URL

Return a JSON object with these fields. Use null for missing fields.

SKIP (return {{"skip": true}}) if:
- Business is in a different state than {location}
- Business is in a city far from {location} (e.g., California when searching West Virginia)
- This is a national company website with no local presence shown
- This is not a {category} or related business

Website content:
{content}

JSON object:"""


class SmartContractorScraper:
    """Multi-stage scraper: Discovers websites via Google, then scrapes each for contact info"""

    def __init__(self, thread_count: int = 5, verbose: bool = True, job_id: int = 0):
        self.thread_count = thread_count
        self.verbose = verbose
        self.job_id = job_id
        self.logger = logging.getLogger("SCRAPER")
        self.client = OpenAI()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._discovered_urls: Set[str] = set()
        self._scraped_domains: Set[str] = set()
        self._contractors_found = 0
        self._log(f"Smart Scraper initialized with {thread_count} threads")

    def _log(self, message: str, level: str = "info"):
        prefix = f"[Job {self.job_id}]" if self.job_id else ""
        msg = f"{prefix} {message}"
        getattr(self.logger, level)(msg)

    def stop(self):
        self._stop_event.set()
        self._log("STOP signal sent")

    def _should_stop(self) -> bool:
        return self._stop_event.is_set()

    def _get_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""

    def _should_skip_url(self, url: str) -> bool:
        domain = self._get_domain(url)
        for skip in SKIP_DOMAINS:
            if skip in domain:
                return True
        return False

    def _create_browser(self):
        """Create a new browser instance"""
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
        return playwright, browser

    def _create_page(self, browser):
        """Create a new page with anti-detection"""
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return context.new_page()

    def _extract_urls_from_google(self, page, search_term: str, location: str) -> List[dict]:
        """Search Google and extract business URLs"""
        urls = []

        try:
            query = f"{search_term} {location}"
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=20"

            self._log(f"[DISCOVER] Searching Google: '{query}'")

            page.goto(url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)
            time.sleep(random.uniform(1, 2))
            page.mouse.wheel(0, 500)
            time.sleep(random.uniform(0.5, 1))

            # Extract all links from the page
            links = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    if (href && href.startsWith('http') && !href.includes('google.com')) {
                        results.push({
                            url: href,
                            text: a.innerText.slice(0, 100)
                        });
                    }
                });
                return results;
            }""")

            self._log(f"[DISCOVER] Found {len(links)} raw links")

            # Filter to business-like URLs
            for link in links:
                url = link.get('url', '')
                if url and not self._should_skip_url(url):
                    domain = self._get_domain(url)
                    if domain and domain not in self._scraped_domains:
                        # Clean URL to just the domain
                        parsed = urlparse(url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}"
                        if clean_url not in self._discovered_urls:
                            self._discovered_urls.add(clean_url)
                            urls.append({
                                'url': clean_url,
                                'name': link.get('text', '')[:50]
                            })

            self._log(f"[DISCOVER] Filtered to {len(urls)} potential business sites")

        except Exception as e:
            self._log(f"[DISCOVER] Error: {e}", "error")

        return urls

    def _scrape_business_website(self, url: str, category: str, location: str, thread_id: str) -> Optional[Contractor]:
        """Scrape a single business website for contact info"""
        if self._should_stop():
            return None

        domain = self._get_domain(url)

        # Skip if already scraped this domain
        with self._lock:
            if domain in self._scraped_domains:
                return None
            self._scraped_domains.add(domain)

        playwright = None
        browser = None

        try:
            self._log(f"[{thread_id}] Scraping: {url}")

            playwright, browser = self._create_browser()
            page = self._create_page(browser)

            try:
                page.goto(url, wait_until='domcontentloaded', timeout=WEBSITE_TIMEOUT)
            except:
                self._log(f"[{thread_id}] Timeout on {domain}, trying anyway...", "warning")

            if self._should_stop():
                return None

            # Get page content
            text_content = page.evaluate("() => document.body.innerText")

            if len(text_content) < 100:
                self._log(f"[{thread_id}] {domain}: Too little content, skipping")
                return None

            self._log(f"[{thread_id}] {domain}: Got {len(text_content)} chars, extracting...")

            # Try to find About/Contact/Team pages for owner info
            extra_content = ""
            pages_to_try = ['about', 'contact', 'team', 'our-team', 'meet-the-team', 'about-us', 'our-story']

            try:
                # Find all relevant links
                found_links = page.evaluate("""() => {
                    const links = document.querySelectorAll('a');
                    const found = [];
                    const keywords = ['about', 'contact', 'team', 'owner', 'founder', 'story', 'who we are'];
                    for (let a of links) {
                        const text = a.innerText.toLowerCase();
                        const href = a.href.toLowerCase();
                        for (let kw of keywords) {
                            if ((text.includes(kw) || href.includes(kw)) && a.href.startsWith('http')) {
                                found.push(a.href);
                                break;
                            }
                        }
                    }
                    return [...new Set(found)].slice(0, 3);  // Max 3 pages
                }""")

                for link in found_links:
                    if self._should_stop():
                        break
                    try:
                        page.goto(link, wait_until='domcontentloaded', timeout=WEBSITE_TIMEOUT)
                        page_text = page.evaluate("() => document.body.innerText")
                        extra_content += "\n\n--- " + link.split('/')[-1].upper() + " PAGE ---\n" + page_text[:3000]
                        self._log(f"[{thread_id}] {domain}: Scraped {link.split('/')[-1]} page (+{len(page_text)} chars)")
                    except:
                        pass
            except:
                pass

            # Combine content - prioritize extra pages as they often have owner info
            full_content = text_content[:6000] + "\n\n" + extra_content[:6000]

            # Extract with AI
            contractor = self._extract_contact_with_ai(full_content, url, category, location, thread_id)

            return contractor

        except Exception as e:
            self._log(f"[{thread_id}] Error on {domain}: {e}", "error")
            return None

        finally:
            try:
                if browser:
                    browser.close()
                if playwright:
                    playwright.stop()
            except:
                pass

    def _extract_contact_with_ai(self, content: str, url: str, category: str, location: str, thread_id: str) -> Optional[Contractor]:
        """Use AI to extract contact info from website content"""
        try:
            prompt = EXTRACT_PROMPT.format(
                content=content[:12000],
                category=category,
                location=location
            )

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract contact info. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                timeout=20
            )

            result = response.choices[0].message.content.strip()

            # Parse JSON
            start = result.find('{')
            end = result.rfind('}')
            if start != -1 and end != -1:
                result = result[start:end+1]

            data = json.loads(result)

            if data.get('skip'):
                reason = data.get('reason', 'not relevant')
                self._log(f"[{thread_id}] AI says skip ({reason})")
                return None

            name = data.get('name')
            if not name:
                return None

            # Server-side location validation
            extracted_state = data.get('state', '').upper().strip() if data.get('state') else None
            extracted_city = data.get('city', '').lower().strip() if data.get('city') else None

            # Parse expected location (e.g., "Martinsburg, WV")
            location_parts = location.split(',')
            expected_city = location_parts[0].strip().lower() if len(location_parts) > 0 else ''
            expected_state = location_parts[1].strip().upper() if len(location_parts) > 1 else ''

            # Reject if state doesn't match (strict validation)
            if extracted_state and expected_state and extracted_state != expected_state:
                # Allow neighboring states (MD, VA, PA for WV)
                neighboring = {
                    'WV': ['MD', 'VA', 'PA', 'OH', 'KY'],
                    'MD': ['WV', 'VA', 'PA', 'DE', 'DC'],
                    'VA': ['WV', 'MD', 'NC', 'TN', 'KY', 'DC'],
                    'PA': ['WV', 'MD', 'NY', 'NJ', 'OH', 'DE'],
                }
                allowed_states = [expected_state] + neighboring.get(expected_state, [])
                if extracted_state not in allowed_states:
                    self._log(f"[{thread_id}] REJECTED: {name} - wrong state ({extracted_state} not near {expected_state})")
                    return None

            owner_name = data.get('owner_name')

            contractor = Contractor(
                name=name,
                owner_name=owner_name,
                category=category,
                address=data.get('address'),
                city=data.get('city'),
                state=data.get('state'),
                zip_code=data.get('zip_code'),
                phone=data.get('phone'),
                email=data.get('email'),
                website=url,
                source=self._get_domain(url),
                location_searched=location
            )

            owner_info = f"Owner: {owner_name}" if owner_name else "No owner found"
            self._log(f"[{thread_id}] EXTRACTED: {name} | {owner_info} | {data.get('phone', 'No phone')}")

            return contractor

        except Exception as e:
            self._log(f"[{thread_id}] AI extraction error: {e}", "error")
            return None

    def _discover_phase(self, categories: List[str], location: str) -> List[Tuple[str, str, str]]:
        """Phase 1: Discover business URLs from Google searches"""
        self._log("=" * 60)
        self._log("PHASE 1: DISCOVERING BUSINESS WEBSITES")
        self._log("=" * 60)

        all_urls = []
        playwright = None
        browser = None

        try:
            playwright, browser = self._create_browser()
            page = self._create_page(browser)

            for category in categories:
                if self._should_stop():
                    break

                search_terms = CATEGORY_SEARCH_TERMS.get(category, [category])

                for term in search_terms:
                    if self._should_stop():
                        break

                    urls = self._extract_urls_from_google(page, term, location)

                    for url_info in urls:
                        all_urls.append((url_info['url'], category, url_info.get('name', '')))

                    time.sleep(random.uniform(1, 2))

        finally:
            try:
                if browser:
                    browser.close()
                if playwright:
                    playwright.stop()
            except:
                pass

        self._log(f"DISCOVERY COMPLETE: Found {len(all_urls)} unique business websites to scrape")
        return all_urls

    def _scrape_phase(
        self,
        urls: List[Tuple[str, str, str]],
        location: str,
        contractor_callback: Optional[Callable] = None
    ) -> List[Contractor]:
        """Phase 2: Scrape each discovered website for contact info"""
        self._log("=" * 60)
        self._log(f"PHASE 2: SCRAPING {len(urls)} BUSINESS WEBSITES")
        self._log(f"Using {self.thread_count} parallel threads")
        self._log("=" * 60)

        all_contractors = []
        completed = 0

        def process_url(args):
            url, category, hint_name = args
            idx = threading.current_thread().name.split('_')[-1]
            thread_id = f"T{idx}"

            if self._should_stop():
                return None

            return self._scrape_business_website(url, category, location, thread_id)

        try:
            with ThreadPoolExecutor(max_workers=self.thread_count, thread_name_prefix='Scraper') as executor:
                future_to_url = {executor.submit(process_url, url_info): url_info for url_info in urls}

                for future in as_completed(future_to_url):
                    if self._should_stop():
                        self._log("Stop requested - cancelling remaining tasks")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    completed += 1
                    url_info = future_to_url[future]

                    try:
                        contractor = future.result(timeout=60)

                        if contractor:
                            with self._lock:
                                all_contractors.append(contractor)
                                self._contractors_found += 1

                            if contractor_callback:
                                contractor_callback(contractor)

                            self._log(f"[{completed}/{len(urls)}] SUCCESS: {contractor.name}")
                        else:
                            self._log(f"[{completed}/{len(urls)}] No data from {url_info[0][:50]}")

                    except Exception as e:
                        self._log(f"[{completed}/{len(urls)}] Error: {e}", "error")

        except Exception as e:
            self._log(f"Thread pool error: {e}", "error")

        return all_contractors

    def scrape_all(
        self,
        categories: List[str],
        location: str,
        progress_callback: Optional[Callable] = None,
        contractor_callback: Optional[Callable] = None,
        should_stop: Optional[Callable] = None
    ) -> List[Contractor]:
        """Main entry: Two-phase smart scraping"""

        self._log("#" * 60)
        self._log("SMART CONTRACTOR SCRAPER")
        self._log(f"  Location: {location}")
        self._log(f"  Categories: {len(categories)}")
        self._log(f"  Threads: {self.thread_count}")
        self._log("#" * 60)

        # Phase 1: Discover URLs
        if progress_callback:
            progress_callback("Discovering websites...", 0, len(categories))

        discovered_urls = self._discover_phase(categories, location)

        if self._should_stop() or (should_stop and should_stop()):
            self._log("Stopped during discovery phase")
            return []

        if not discovered_urls:
            self._log("No websites discovered!")
            return []

        # Phase 2: Scrape each URL
        if progress_callback:
            progress_callback("Scraping websites...", 1, 2)

        contractors = self._scrape_phase(discovered_urls, location, contractor_callback)

        self._log("#" * 60)
        self._log(f"COMPLETE: {len(contractors)} contractors extracted")
        self._log("#" * 60)

        return contractors


# Backwards compatible alias
class ContractorScraper(SmartContractorScraper):
    def cleanup(self):
        self.stop()

    def scrape_all_categories(
        self,
        categories: List[str],
        location: str,
        progress_callback: Optional[Callable] = None,
        contractor_callback: Optional[Callable] = None,
        should_stop: Optional[Callable] = None
    ) -> List[Contractor]:
        return self.scrape_all(
            categories=categories,
            location=location,
            progress_callback=progress_callback,
            contractor_callback=contractor_callback,
            should_stop=should_stop
        )
