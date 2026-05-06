#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Job Scraper - Quick Start (for local testing, not Docker)
# ─────────────────────────────────────────────────────────────────────────────

echo "🚀 LinkedIn Job Scraper - Local Setup"
echo "====================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python 3 is installed"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the API server, run:"
echo "   source venv/bin/activate"
echo "   uvicorn api.main:app --reload"
echo ""
echo "📊 Then open: http://localhost:8000"
echo ""
echo "⚠️  Note: You'll need MongoDB running separately:"
echo "   MongoDB URI: mongodb://localhost:27017"
