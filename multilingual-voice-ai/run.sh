#!/bin/bash

# AI Voice Bus System Startup Script

echo "🚀 Starting AI Voice Bus System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p twilio_audio static/audio utils

# Check environment file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found! Please create one with your Twilio credentials."
    echo "See .env example in the documentation."
    exit 1
fi

echo "🎯 Starting FastAPI server..."
echo "📱 Don't forget to set up ngrok: ngrok http 8000"
echo "🔗 Then update your Twilio webhook URL to: https://your-ngrok-url.ngrok.io/voice"

# Start the server
python main.py
