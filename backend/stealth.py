"""
Stealth & Anti-Detection Module
Provides rotating User-Agents, proxy support, and browser fingerprint evasion.
"""

import random
import os
from typing import Optional, Dict, List
from dataclasses import dataclass

# Rotating User-Agents (updated Chrome/Firefox/Safari versions)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# Viewport sizes (common screen resolutions)
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 2560, "height": 1440},
    {"width": 1680, "height": 1050},
]

# Timezone IDs matching common US locations
TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
]

# Locales
LOCALES = ["en-US", "en-GB", "en-CA"]


@dataclass
class ProxyConfig:
    """Proxy configuration for rotating IPs."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def playwright_config(self) -> Dict:
        config = {"server": f"{self.protocol}://{self.host}:{self.port}"}
        if self.username and self.password:
            config["username"] = self.username
            config["password"] = self.password
        return config


class StealthConfig:
    """Manages stealth settings for browser automation."""

    def __init__(self):
        self._request_count = 0
        self._proxies: List[ProxyConfig] = []
        self._load_proxies()

    def _load_proxies(self):
        """Load proxy configuration from environment."""
        # Support for common proxy formats:
        # PROXY_URL=http://user:pass@host:port
        # or BRIGHTDATA_PROXY, SMARTPROXY_URL, etc.

        proxy_url = os.environ.get("PROXY_URL") or os.environ.get("BRIGHTDATA_PROXY") or os.environ.get("SMARTPROXY_URL")

        if proxy_url:
            try:
                # Parse proxy URL
                from urllib.parse import urlparse
                parsed = urlparse(proxy_url)
                self._proxies.append(ProxyConfig(
                    host=parsed.hostname or "",
                    port=parsed.port or 80,
                    username=parsed.username,
                    password=parsed.password,
                    protocol=parsed.scheme or "http"
                ))
            except Exception:
                pass

        # Also check for multiple proxies (comma-separated)
        proxy_list = os.environ.get("PROXY_LIST", "").strip()
        if proxy_list:
            for proxy_url in proxy_list.split(","):
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(proxy_url.strip())
                    self._proxies.append(ProxyConfig(
                        host=parsed.hostname or "",
                        port=parsed.port or 80,
                        username=parsed.username,
                        password=parsed.password,
                        protocol=parsed.scheme or "http"
                    ))
                except Exception:
                    pass

    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0

    def get_random_user_agent(self) -> str:
        """Get a random User-Agent string."""
        return random.choice(USER_AGENTS)

    def get_random_viewport(self) -> Dict:
        """Get a random viewport size."""
        return random.choice(VIEWPORTS).copy()

    def get_random_timezone(self) -> str:
        """Get a random timezone."""
        return random.choice(TIMEZONES)

    def get_random_locale(self) -> str:
        """Get a random locale."""
        return random.choice(LOCALES)

    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get the next proxy in rotation."""
        if not self._proxies:
            return None
        self._request_count += 1
        return self._proxies[self._request_count % len(self._proxies)]

    def get_browser_args(self) -> List[str]:
        """Get Chromium launch arguments for stealth."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-infobars",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-extensions-with-background-pages",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-features=TranslateUI",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-renderer-backgrounding",
            "--disable-sync",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--no-first-run",
            "--no-sandbox",
            "--password-store=basic",
            "--use-mock-keychain",
        ]

    def get_stealth_scripts(self) -> List[str]:
        """Get JavaScript scripts to inject for stealth."""
        return [
            # Hide webdriver
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",

            # Fix plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
                    {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}
                ]
            })
            """,

            # Fix languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",

            # Fix platform
            "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})",

            # Fix hardware concurrency
            "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})",

            # Fix device memory
            "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})",

            # Chrome property
            """
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            }
            """,

            # Permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            )
            """,

            # WebGL vendor
            """
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, arguments);
            }
            """,
        ]


# Global instance
stealth = StealthConfig()


def get_stealth_context_options(stealth_config: StealthConfig = None) -> Dict:
    """Get Playwright context options with stealth settings."""
    config = stealth_config or stealth

    options = {
        "viewport": config.get_random_viewport(),
        "user_agent": config.get_random_user_agent(),
        "locale": config.get_random_locale(),
        "timezone_id": config.get_random_timezone(),
        "permissions": ["geolocation"],
        "geolocation": {"latitude": 39.0, "longitude": -77.5},  # DC area
        "color_scheme": "light",
        "reduced_motion": "no-preference",
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 1,
    }

    # Add proxy if available
    proxy = config.get_next_proxy()
    if proxy:
        options["proxy"] = proxy.playwright_config

    return options


def apply_stealth_scripts(page) -> None:
    """Apply stealth scripts to a Playwright page."""
    for script in stealth.get_stealth_scripts():
        try:
            page.add_init_script(script)
        except Exception:
            pass
