#!/bin/bash
# One-time setup: Generate LinkedIn cookies locally using Docker
# Usage: ./generate_cookies.sh

# Load .env variables (email and password)
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy from .env.template and add credentials."
    exit 1
fi

source .env

if [ -z "$LINKEDIN_SEARCH_EMAIL" ] || [ -z "$LINKEDIN_SEARCH_PASSWORD" ]; then
    echo "❌ LINKEDIN_SEARCH_EMAIL and LINKEDIN_SEARCH_PASSWORD must be set in .env"
    exit 1
fi

echo "🔨 Building Docker image..."
docker build -t linkedin-scraper:temp .

echo "🌐 Launching browser to log in and save cookies..."
echo "   You will see a browser window. Complete any CAPTCHA/2FA, then press ENTER in the prompt."
echo ""

# Enable X11 forwarding so Docker can display the browser on your host
if [ -z "$DISPLAY" ]; then
    echo "⚠️  WARNING: DISPLAY is not set. Browser window may not appear."
    echo "   On Linux with X11, try: export DISPLAY=:0"
    echo "   Attempting to continue anyway..."
fi

docker run -it --rm \
  -e LINKEDIN_SEARCH_EMAIL="$LINKEDIN_SEARCH_EMAIL" \
  -e LINKEDIN_SEARCH_PASSWORD="$LINKEDIN_SEARCH_PASSWORD" \
  -e HEADLESS=false \
  -e BROWSER=chrome \
  -e DISPLAY=${DISPLAY:-:0} \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$(pwd)":/app \
  linkedin-scraper:temp \
  python save_session.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Cookies saved! You can now run the full Docker services:"
    echo ""
    echo "   docker-compose up -d"
    echo ""
else
    echo "❌ Cookie generation failed. Check the error above."
    exit 1
fi
