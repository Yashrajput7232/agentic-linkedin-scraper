import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
import time
import requests
import pandas as pd
from dotenv import load_dotenv

from scripts.helpers import strip_val, get_value_by_path

load_dotenv()

HEADLESS    = os.getenv("HEADLESS",    "false").strip().lower() == "true"


def _normalize_browser(value: str, default: str = "edge") -> str:
    if not value:
        return default
    value = value.strip()
    normalized = value.lower()
    if normalized in {"chrome", "chromium", "google-chrome", "google chrome", "googlechrome"}:
        return "chrome"
    if normalized in {"edge", "msedge", "microsoft-edge", "microsoft edge", "microsoftedge"}:
        return "edge"
    if os.path.sep in value or value.startswith("."):
        if "chrome" in normalized or "chromium" in normalized or "google" in normalized:
            return "chrome"
        if "edge" in normalized or "msedge" in normalized or "microsoft" in normalized:
            return "edge"
        return default
    return value


BROWSER     = _normalize_browser(os.getenv("BROWSER", "edge"))
COOKIE_FILE = os.getenv("COOKIE_FILE", "linkedin_cookies.json")


# ---------------------------------------------------------------------------
# Cookie-file helpers (used when HEADLESS=true / Docker)
# ---------------------------------------------------------------------------

def _load_session_from_file(email: str) -> requests.Session | None:
    """
    Try to build a session from LINKEDIN_COOKIES_JSON env var or linkedin_cookies.json.
    Returns a Session if cookies are still valid, None otherwise.
    """
    import json
    
    all_cookies = None
    
    # 1. Try from Environment Variable
    env_cookies = os.getenv("LINKEDIN_COOKIES_JSON")
    if env_cookies:
        try:
            all_cookies = json.loads(env_cookies)
        except Exception as e:
            print(f"[Session] Failed to parse LINKEDIN_COOKIES_JSON from .env: {e}")
    
    # 2. Try from File (Fallback)
    if all_cookies is None:
        if not os.path.exists(COOKIE_FILE):
            return None
        if os.path.isdir(COOKIE_FILE):
            print(f"[Session] COOKIE_FILE path is a directory, expected JSON file: {COOKIE_FILE}")
            return None
        try:
            with open(COOKIE_FILE) as f:
                all_cookies = json.load(f)
        except Exception:
            return None

    if email not in all_cookies:
        print(f"[Session] No saved cookies found for {email} in {COOKIE_FILE}")
        return None

    session = requests.Session()
    for name, value in all_cookies[email].items():
        session.cookies.set(name, value)

    # Quick validity check
    try:
        resp = session.get(
            "https://www.linkedin.com/feed/",
            allow_redirects=False,
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"[Session] ✓ Valid saved cookies loaded for {email}")
            return session
        print(f"[Session] Saved cookies for {email} are expired (status={resp.status_code})")
    except Exception as e:
        print(f"[Session] Cookie check failed: {e}")
    return None


def _build_driver():
    """
    Build a Selenium WebDriver based on BROWSER and HEADLESS env vars.

    HEADLESS=true  → Chrome with headless flags (required for Docker / no display)
    HEADLESS=false → visible Chrome or Edge window (default for local use)
    """
    if HEADLESS:
        # Headless Chrome — only Chrome is supported in Docker
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")          # new headless mode (Chrome 112+)
        options.add_argument("--no-sandbox")             # required in Docker
        options.add_argument("--disable-dev-shm-usage")  # avoid /dev/shm size issues
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    # ── GUI mode (local machine) ─────────────────────────────────────────
    if BROWSER == "chrome":
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service)
    elif BROWSER == "edge":
        service = EdgeService(EdgeChromiumDriverManager().install())
        return webdriver.Edge(service=service)
    else:
        raise ValueError(
            f"Unsupported BROWSER value: {BROWSER!r}. Use 'chrome' or 'edge', or leave BROWSER unset."
        )


def create_session(email: str, password: str) -> requests.Session:
    """
    Return an authenticated LinkedIn requests.Session.

    Priority:
      1. Load from COOKIE_FILE (linkedin_cookies.json) — no browser needed.
         Run save_session.py locally once to generate this file.
      2. Headless browser login (HEADLESS=true) — auto-detects success via URL.
      3. GUI browser login (HEADLESS=false) — prompts user to press ENTER.
    """
    # ── 1. Try saved cookies first (fastest, works in Docker) ────────────────
    session = _load_session_from_file(email)
    if session:
        return session

    if HEADLESS:
        raise RuntimeError(
            f"No valid saved cookies found for {email} and HEADLESS=true.\n"
            f"Run locally first:\n"
            f"  HEADLESS=false python save_session.py\n"
            f"Then copy linkedin_cookies.json into Docker (see docker-compose.yml volumes)."
        )

    # ── 2. GUI browser login ─────────────────────────────────────────────────
    print(f"[Login] Opening browser for {email}...")
    driver = _build_driver()
    wait   = WebDriverWait(driver, 15)

    driver.get("https://www.linkedin.com/checkpoint/rm/sign-in-another-account")
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)

    try:
        sign_in_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
    except Exception:
        sign_in_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//button[contains(translate(text(),"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]")
            )
        )
    sign_in_btn.click()

    input(f'Press ENTER after a successful login for "{email}": ')

    driver.get("https://www.linkedin.com/jobs/search/?")
    time.sleep(2)
    raw_cookies = driver.get_cookies()
    driver.quit()

    session = requests.Session()
    for cookie in raw_cookies:
        session.cookies.set(cookie["name"], cookie["value"])
    return session


def _load_credentials(emails_env: str, passwords_env: str):
    """
    Read comma-separated email / password lists from environment variables.
    Returns (emails: list[str], passwords: list[str]).
    """
    emails_raw    = os.environ.get(emails_env, "")
    passwords_raw = os.environ.get(passwords_env, "")

    emails    = [e.strip() for e in emails_raw.split(",")    if e.strip()]
    passwords = [p.strip() for p in passwords_raw.split(",") if p.strip()]

    if not emails or not passwords:
        raise EnvironmentError(
            f"Missing credentials — set {emails_env} and {passwords_env} in your .env file."
        )
    if len(emails) != len(passwords):
        raise EnvironmentError(
            f"Mismatch: {len(emails)} email(s) but {len(passwords)} password(s) "
            f"in {emails_env} / {passwords_env}."
        )
    return emails, passwords


# ---------------------------------------------------------------------------
# Retrievers
# ---------------------------------------------------------------------------

class JobSearchRetriever:
    """
    Supports multiple keyword groups (semicolon-separated in LINKEDIN_SEARCH_KEYWORD_GROUPS).
    Each group becomes a separate search URL. On every get_jobs() call the next group
    is used, rotating through all groups in order.

    LinkedIn API filters applied from .env:
      LINKEDIN_EXPERIENCE_LEVELS  e.g. 2,3          (2=Entry, 3=Associate)
      LINKEDIN_DATE_POSTED        e.g. r2592000      (r86400=24h, r604800=week, r2592000=month)
      LINKEDIN_JOB_TYPE           e.g. F             (F=Full-time, P=Part-time, C=Contract)
      LINKEDIN_GEO_IDS            e.g. 105214791,105214831,105556813  (Pune,Bangalore,Hyderabad)
      LINKEDIN_WORKPLACE_TYPES    e.g. 1,2,3         (1=On-site, 2=Remote, 3=Hybrid)
    """

    BASE_URL = (
        "https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards"
        "?decorationId=com.linkedin.voyager.dash.deco.jobs.search"
        ".JobSearchCardsCollection-187&count=100&q=jobSearch"
    )

    def __init__(self):
        filter_str = self._build_filter_str()
        self.job_search_links = self._build_search_urls(filter_str)
        self.link_index = 0

        print(f"[Search] {len(self.job_search_links)} keyword group(s) loaded")
        for i, url in enumerate(self.job_search_links, 1):
            # Extract the readable keyword portion from the URL for display
            kw_start = url.find("keywords:") + len("keywords:")
            kw_end   = url.find(",origin")
            kw_display = url[kw_start:kw_end].replace("%20", " ") if kw_start > 9 else "(all jobs)"
            print(f"  Group {i}: {kw_display}")

        emails, passwords = _load_credentials(
            "LINKEDIN_SEARCH_EMAIL", "LINKEDIN_SEARCH_PASSWORD"
        )
        self.sessions      = [create_session(e, p) for e, p in zip(emails, passwords)]
        self.session_index = 0
        self.headers       = self._build_headers()

    def _build_filter_str(self) -> str:
        """Construct the selectedFilters(...) content from env vars."""
        filters = ["sortBy:List(DD)"]

        # Experience levels: 2=Entry level, 3=Associate
        exp = os.getenv("LINKEDIN_EXPERIENCE_LEVELS", "").strip()
        if exp:
            filters.append(f"experience:List({exp})")

        # Date posted: r86400=24h, r604800=1 week, r2592000=1 month
        date_posted = os.getenv("LINKEDIN_DATE_POSTED", "").strip()
        if date_posted:
            filters.append(f"timePostedRange:List({date_posted})")

        # Job type: F=Full-time, P=Part-time, C=Contract, T=Temporary
        job_type = os.getenv("LINKEDIN_JOB_TYPE", "").strip()
        if job_type:
            filters.append(f"contractType:List({job_type})")

        # Geo URNs for location (Pune, Bangalore, Hyderabad, etc.)
        geo_ids = os.getenv("LINKEDIN_GEO_IDS", "").strip()
        if geo_ids:
            geo_list = ",".join(
                f"urn%3Ali%3Ageo%3A{gid.strip()}"
                for gid in geo_ids.split(",") if gid.strip()
            )
            filters.append(f"geoUrn:List({geo_list})")

        # Workplace type: 1=On-site, 2=Remote, 3=Hybrid
        workplace = os.getenv("LINKEDIN_WORKPLACE_TYPES", "").strip()
        if workplace:
            filters.append(f"workplaceType:List({workplace})")

        return ",".join(filters)

    def _build_search_urls(self, filter_str: str) -> list:
        """
        Build one URL per keyword group.
        Groups are semicolon-separated in LINKEDIN_SEARCH_KEYWORD_GROUPS.
        Within each group, keywords are comma-separated and joined with %20 OR encoding.
        """
        raw_groups = os.getenv("LINKEDIN_SEARCH_KEYWORD_GROUPS", "").strip()
        groups = [g.strip() for g in raw_groups.split(";") if g.strip()] if raw_groups else [""]

        urls = []
        for group in groups:
            if group:
                # Each keyword phrase is URL-encoded; phrases joined with %20OR%20
                phrases = [k.strip().replace(" ", "%20") for k in group.split(",") if k.strip()]
                encoded = "%20OR%20".join(phrases)
                keyword_part = f"keywords:{encoded},"
            else:
                keyword_part = ""

            url = (
                f"{self.BASE_URL}"
                f"&query=({keyword_part}origin:JOB_SEARCH_PAGE_OTHER_ENTRY,"
                f"selectedFilters:({filter_str}),spellCorrectionEnabled:true)&start=0"
            )
            urls.append(url)
        return urls

    def _build_headers(self):
        return [
            {
                "Authority":        "www.linkedin.com",
                "Method":           "GET",
                "Scheme":           "https",
                "Accept":           "application/vnd.linkedin.normalized+json+2.1",
                "Accept-Encoding":  "gzip, deflate, br",
                "Accept-Language":  "en-US,en;q=0.9",
                "Cookie":           "; ".join(
                    [f"{k}={v}" for k, v in session.cookies.items()]
                ),
                "Csrf-Token":       session.cookies.get("JSESSIONID", "").strip('"'),
                "User-Agent":       (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/117.0.0.0 Safari/537.36"
                ),
                "X-Li-Track": (
                    '{"clientVersion":"1.13.5589","mpVersion":"1.13.5589",'
                    '"osName":"web","timezoneOffset":-7,"timezone":"America/Los_Angeles",'
                    '"deviceFormFactor":"DESKTOP","mpName":"voyager-web",'
                    '"displayDensity":1,"displayWidth":360,"displayHeight":800}'
                ),
            }
            for session in self.sessions
        ]

    def get_jobs(self) -> dict:
        # Rotate through keyword groups on each call
        url   = self.job_search_links[self.link_index]
        group_num = self.link_index + 1
        self.link_index = (self.link_index + 1) % len(self.job_search_links)

        print(f"[Search] Querying group {group_num}/{len(self.job_search_links)}...")
        results = self.sessions[self.session_index].get(
            url,
            headers=self.headers[self.session_index],
        )
        self.session_index = (self.session_index + 1) % len(self.sessions)

        if results.status_code != 200:
            raise Exception(
                f"Status code {results.status_code} for search\nText: {results.text}"
            )

        results  = results.json()
        job_ids  = {}

        for r in results["included"]:
            if (
                r["$type"] == "com.linkedin.voyager.dash.jobs.JobPostingCard"
                and "referenceId" in r
            ):
                job_id = int(strip_val(r["jobPostingUrn"], 1))
                job_ids[job_id] = {"sponsored": False}
                job_ids[job_id]["title"] = r.get("jobPostingTitle")
                for x in r["footerItems"]:
                    if x.get("type") == "PROMOTED":
                        job_ids[job_id]["sponsored"] = True
                        break

        return job_ids


class JobDetailRetriever:
    def __init__(self):
        self.error_count      = 0
        self.job_details_link = (
            "https://www.linkedin.com/voyager/api/jobs/jobPostings/{}"
            "?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebFullJobPosting-65"
        )

        emails, passwords = _load_credentials(
            "LINKEDIN_DETAILS_EMAILS", "LINKEDIN_DETAILS_PASSWORDS"
        )
        self.emails        = emails
        self.sessions      = [create_session(e, p) for e, p in zip(emails, passwords)]
        self.session_index = 0
        self.variable_paths = pd.read_csv("json_paths/data_variables.csv")
        self.headers        = self._build_headers()

    def _build_headers(self):
        return [
            {
                "Authority":        "www.linkedin.com",
                "Method":           "GET",
                "Scheme":           "https",
                "Accept":           "application/vnd.linkedin.normalized+json+2.1",
                "Accept-Encoding":  "gzip, deflate, br",
                "Accept-Language":  "en-US,en;q=0.9",
                "Cookie":           "; ".join(
                    [f"{k}={v}" for k, v in session.cookies.items()]
                ),
                "Csrf-Token":       session.cookies.get("JSESSIONID", "").strip('"'),
                "User-Agent":       (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/117.0.0.0 Safari/537.36"
                ),
                "X-Li-Track": (
                    '{"clientVersion":"1.13.5589","mpVersion":"1.13.5589",'
                    '"osName":"web","timezoneOffset":-7,"timezone":"America/Los_Angeles",'
                    '"deviceFormFactor":"DESKTOP","mpName":"voyager-web",'
                    '"displayDensity":1,"displayWidth":360,"displayHeight":800}'
                ),
            }
            for session in self.sessions
        ]

    def get_job_details(self, job_ids) -> dict:
        job_details = {}
        for job_id in job_ids:
            error = False
            try:
                details = self.sessions[self.session_index].get(
                    self.job_details_link.format(job_id),
                    headers=self.headers[self.session_index],
                )
            except requests.exceptions.Timeout:
                print(f"Timeout for job {job_id}")
                error = True

            if not error and details.status_code != 200:
                job_details[job_id] = -1
                print(
                    f"Status code {details.status_code} for job {job_id} "
                    f"with account {self.emails[self.session_index]}\n"
                    f"Text: {details.text}"
                )
                error = True

            if error:
                self.error_count += 1
                if self.error_count > 10:
                    raise Exception("Too many errors")
            else:
                self.error_count = 0
                job_details[job_id] = details.json()
                print(f"Job {job_id} done")

            self.session_index = (self.session_index + 1) % len(self.sessions)
            time.sleep(0.3)

        return job_details
