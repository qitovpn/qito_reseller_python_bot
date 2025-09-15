#!/bin/bash

# Production deployment script for QitopyBot

set -e

echo "🚀 Starting QitopyBot deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with the following variables:"
    echo "BOT_TOKEN=your_telegram_bot_token_here"
    echo "ADMIN_TELEGRAM_ID=your_admin_telegram_id_here"
    exit 1
fi

# Create data directory for persistent storage
mkdir -p data

# Build Docker image
echo "📦 Building Docker image..."
docker build -t qitopybot:latest .

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker-compose down || true

# Start the application
echo "▶️ Starting QitopyBot..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for application to start..."
sleep 10

# Check if container is running
if docker-compose ps | grep -q "Up"; then
    echo "✅ QitopyBot is running successfully!"
    echo "🌐 Web admin panel: http://localhost:5000"
    echo "📱 Telegram bot is active"
    echo ""
    echo "📊 Container status:"
    docker-compose ps
    echo ""
    echo "📋 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
else
    echo "❌ Failed to start QitopyBot"
    echo "📋 Check logs: docker-compose logs"
    exit 1
fi
