"""
save_session.py — Run this ONCE locally (GUI mode) to save LinkedIn cookies.

Usage:
    python save_session.py

It opens a browser, logs in with your .env credentials, and saves the cookies
to linkedin_cookies.json. Docker then loads those cookies instead of logging in.

Cookies typically last 1–2 weeks. Re-run when Docker starts getting 401 errors.
"""

import os
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
import time
from dotenv import load_dotenv

load_dotenv()

COOKIE_FILE = os.getenv("COOKIE_FILE", "linkedin_cookies.json")


def _normalize_browser(value: str, default: str = "chrome") -> str:
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


BROWSER     = _normalize_browser(os.getenv("BROWSER", "chrome"))


def gui_login(email: str, password: str) -> requests.Session:
    """Open a visible browser, log in, return session with cookies."""
    # Try pre-installed ChromeDriver first (Docker), fallback to webdriver-manager (local)
    driver = None
    
    if BROWSER == "chrome":
        try:
            # Try Docker's pre-installed ChromeDriver first
            service = ChromeService("/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service)
        except (FileNotFoundError, Exception):
            # Fallback: use webdriver-manager for local machine
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service)
    elif BROWSER == "edge":
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service)
    else:
        raise ValueError(
            f"Unsupported BROWSER: {BROWSER!r}. Use 'chrome' or 'edge', or leave BROWSER unset."
        )

    wait = WebDriverWait(driver, 15)
    driver.get("https://www.linkedin.com/checkpoint/rm/sign-in-another-account")

    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)

    try:
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    except Exception:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(translate(text(),"
             "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]")
        ))
    btn.click()

    input(f'\nComplete any CAPTCHA/2FA, then press ENTER to save cookies for "{email}": ')

    driver.get("https://www.linkedin.com/jobs/search/?")
    time.sleep(2)

    raw_cookies = driver.get_cookies()
    driver.quit()

    session = requests.Session()
    cookie_dict = {}
    for c in raw_cookies:
        session.cookies.set(c["name"], c["value"])
        cookie_dict[c["name"]] = c["value"]

    return session, cookie_dict


def _load_cookie_file() -> dict:
    if os.path.isdir(COOKIE_FILE):
        raise IsADirectoryError(
            f"COOKIE_FILE path is a directory, but a JSON file is required: {COOKIE_FILE!r}."
            " Remove the directory or set COOKIE_FILE to a file path."
        )
    if not os.path.exists(COOKIE_FILE):
        return {}
    with open(COOKIE_FILE) as f:
        return json.load(f)


def main():
    emails    = [e.strip() for e in os.environ.get("LINKEDIN_SEARCH_EMAIL",  "").split(",") if e.strip()]
    passwords = [p.strip() for p in os.environ.get("LINKEDIN_SEARCH_PASSWORD", "").split(",") if p.strip()]
    # Also include detail accounts
    emails    += [e.strip() for e in os.environ.get("LINKEDIN_DETAILS_EMAILS",    "").split(",") if e.strip()]
    passwords += [p.strip() for p in os.environ.get("LINKEDIN_DETAILS_PASSWORDS", "").split(",") if p.strip()]

    # Deduplicate preserving order
    seen, unique_pairs = set(), []
    for e, p in zip(emails, passwords):
        if e not in seen:
            seen.add(e)
            unique_pairs.append((e, p))

    all_cookies = _load_cookie_file()

    for email, password in unique_pairs:
        print(f"\n── Logging in as {email} ──")
        _, cookie_dict = gui_login(email, password)
        all_cookies[email] = cookie_dict
        print(f"✓ Saved {len(cookie_dict)} cookies for {email}")

    with open(COOKIE_FILE, "w") as f:
        json.dump(all_cookies, f, indent=2)

    print(f"\n✅ All cookies saved to {COOKIE_FILE}")
    print(   "   Mount this file into Docker and set COOKIE_FILE=/app/linkedin_cookies.json")


if __name__ == "__main__":
    main()
