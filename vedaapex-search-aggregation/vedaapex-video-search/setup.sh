#!/bin/bash

# VedaApex Video Search Backend - Setup Script (macOS/Linux)
# This script sets up the development environment

set -e  # Exit on error

echo "======================================"
echo "VedaApex Video Search Backend - Setup"
echo "======================================"
echo ""

# Check Python version
echo "✓ Checking Python installation..."
python3 --version || { echo "Python 3 is required but not installed."; exit 1; }

# Create virtual environment
echo "✓ Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "✓ Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "✓ Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your Pexels API key:"
    echo "   nano .env"
    echo ""
else
    echo "✓ .env file already exists"
fi

# Create logs directory
echo "✓ Creating logs directory..."
mkdir -p logs

# Verify installation
echo ""
echo "✓ Verifying installation..."
python -c "import fastapi; import pydantic; print('✓ All dependencies installed successfully')" || { echo "Dependency check failed"; exit 1; }

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your Pexels API key"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the server: python app.py"
echo "4. Visit API docs: http://localhost:8000/docs"
echo ""
