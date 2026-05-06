#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Job Scraper - Setup Verification Script
# Checks that all required files and dependencies are in place
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║        LinkedIn Job Scraper - Setup Verification                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
        exit 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
    else
        echo -e "${RED}✗${NC} $1/"
        exit 1
    fi
}

echo "📁 Checking directory structure..."
check_dir "api"
check_dir "api/routes"
check_dir "api/services"
check_dir "frontend"
check_dir "scripts"

echo ""
echo "📄 Checking API files..."
check_file "api/__init__.py"
check_file "api/main.py"
check_file "api/models.py"
check_file "api/database.py"
check_file "api/routes/__init__.py"
check_file "api/routes/jobs.py"
check_file "api/routes/resume.py"
check_file "api/routes/scraper.py"
check_file "api/services/__init__.py"
check_file "api/services/resume_matcher.py"

echo ""
echo "🎨 Checking frontend files..."
check_file "frontend/index.html"
check_file "frontend/styles.css"
check_file "frontend/app.js"

echo ""
echo "🐳 Checking Docker files..."
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file "requirements.txt"

echo ""
echo "📚 Checking documentation..."
check_file "README_API.md"
check_file "SETUP_GUIDE.md"
check_file ".env.template"

echo ""
echo "🔧 Checking setup scripts..."
check_file "quickstart.sh"
check_file "setup_local.sh"
check_file "verify_setup.sh"

echo ""
echo "📋 Checking original files still present..."
check_file "README.md"
check_file "search_retriever.py"
check_file "details_retriever.py"
check_file "logins.csv.template"

echo ""
echo "✅ All files present and accounted for!"
echo ""
echo "Next steps:"
echo "1. Run: bash quickstart.sh     (for Docker setup)"
echo "2. Or:  bash setup_local.sh    (for local setup)"
echo "3. Open: http://localhost:8000"
echo ""
