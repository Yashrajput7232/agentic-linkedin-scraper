# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Job Scraper — Docker image
# Base: Python 3.12 slim + Google Chrome + ChromeDriver
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# ── System deps + Google Chrome ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        gnupg \
        ca-certificates \
        curl \
        unzip \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        xdg-utils \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
        http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── ChromeDriver (matches installed Chrome version automatically) ─────────────
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') && \
    CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}.0/linux64/chromedriver-linux64.zip" && \
    wget -q "$CHROMEDRIVER_URL" -O /tmp/chromedriver.zip || \
    (LATEST=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
     wget -q "https://storage.googleapis.com/chrome-for-testing-public/${LATEST}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip) && \
    unzip /tmp/chromedriver.zip -d /tmp/chromedriver && \
    mv /tmp/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver*

# ── Custom file for startup ──────────────────────────────────────────────────
WORKDIR /app

# ── Copy requirements and install dependencies ────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ────────────────────────────────────────────────────
COPY . .

# ── Expose API port ──────────────────────────────────────────────────────────
EXPOSE 8000

# ── Default command can be overridden in docker-compose ─────────────────────
CMD ["python", "search_retriever.py"]

# ── App setup ────────────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── Environment defaults (override via docker run -e or .env mount) ───────────
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# ── Entrypoint ───────────────────────────────────────────────────────────────
# Default: run the search scraper.
# Override CMD to run details_retriever or match_jobs instead.
CMD ["python", "search_retriever.py"]
