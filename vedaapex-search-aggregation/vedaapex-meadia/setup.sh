#!/bin/bash

# VedaApex Media - Setup Script (macOS/Linux)

echo "🚀 VedaApex Media - Setup Script"
echo "=================================="

# Check Python
python_version=$(python3 --version 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found"
    exit 1
fi
echo "✅ $python_version"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

# Create logs directory
mkdir -p logs

echo ""
echo "✅ Setup completed!"
echo ""
echo "📖 Next steps:"
echo "   1. Update .env with your configuration"
echo "   2. Run: python3 app.py"
echo "   3. Visit: http://localhost:8000/api/v1/docs"
