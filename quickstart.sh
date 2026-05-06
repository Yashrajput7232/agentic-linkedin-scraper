#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Job Scraper - Docker Quick Start
# Simplest way to get everything running
# ─────────────────────────────────────────────────────────────────────────────

set -e

clear
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║       LinkedIn Job Scraper - Docker Quick Start                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check requirements
echo "📋 Checking requirements..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "   Install from: https://docker.com"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    echo "   Install from: https://docker.com"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check for required files
echo "📄 Checking required files..."

if [ ! -f "linkedin_cookies.json" ]; then
    echo "⚠️  linkedin_cookies.json not found"
    echo "   Generate it by running: python generate_cookies.sh"
    echo ""
    read -p "   Would you like to generate it now? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python generate_cookies.sh
    else
        echo "❌ Cannot proceed without LinkedIn cookies"
        exit 1
    fi
fi

echo "✅ LinkedIn cookies found"

if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "✅ .env created (edit if needed)"
fi

echo ""
echo "🔨 Building Docker images..."
echo "   This may take a few minutes..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                        🎉 All Set Up!                              ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📱 Access the Dashboard:"
echo "   http://localhost:8000"
echo ""
echo "📚 API Documentation (Swagger):"
echo "   http://localhost:8000/docs"
echo ""
echo "💾 MongoDB:"
echo "   mongodb://scraper:password@localhost:27017"
echo ""
echo "🎯 Quick Start Guide:"
echo "   1. Open http://localhost:8000 in your browser"
echo "   2. Go to 'Resume' tab"
echo "   3. Upload your resume"
echo "   4. Click 'Analyze & Calculate Relevance Scores'"
echo "   5. Check 'Jobs' tab for results sorted by relevance"
echo "   6. Monitor scraping in 'Scraper' tab"
echo ""
echo "🛑 To stop everything:"
echo "   docker-compose down"
echo ""
echo "📖 For more info: cat SETUP_GUIDE.md"
echo ""
