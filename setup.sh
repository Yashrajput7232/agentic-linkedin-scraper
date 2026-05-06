#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Job Scraper - Complete Setup Script
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo "🚀 LinkedIn Job Scraper - Docker Setup"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

echo "✓ Docker is installed"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker Compose is installed"
echo ""

# Check if cookies file exists
if [ ! -f "linkedin_cookies.json" ]; then
    echo "⚠️  linkedin_cookies.json not found!"
    echo "   You need to generate it using: python generate_cookies.sh"
    echo ""
    read -p "Generate cookies now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python generate_cookies.sh
    else
        echo "❌ Setup cancelled. Please generate linkedin_cookies.json first."
        exit 1
    fi
fi

echo "✓ LinkedIn cookies file found"

# Check if .env exists, create from template if not
if [ ! -f ".env" ]; then
    echo "📄 Creating .env from template..."
    cp .env.template .env
    echo "✓ .env created. Please edit with your MongoDB credentials if needed."
else
    echo "✓ .env file exists"
fi

echo ""
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for MongoDB to be ready..."
sleep 5

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Access the dashboard at: http://localhost:8000"
echo "📚 API documentation at: http://localhost:8000/docs"
echo ""
echo "Services running:"
docker-compose ps

echo ""
echo "📋 Next steps:"
echo "1. Open http://localhost:8000 in your browser"
echo "2. Upload your resume in the 'Resume' tab"
echo "3. Click 'Analyze & Calculate Relevance Scores'"
echo "4. View jobs sorted by relevance in the 'Jobs' tab"
echo "5. Monitor scraping progress in the 'Scraper' tab"
echo ""
echo "📖 For more information, see SETUP_GUIDE.md"
