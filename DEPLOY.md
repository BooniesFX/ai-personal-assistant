# Deployment Guide

This bot is containerized using Docker, making it easy to deploy on any platform that supports Docker (Zeabur, Railway, Render, VPS, etc.).

> **Note**: Vercel is **not recommended** for this bot because it uses long-polling and requires long execution times for image generation, which exceeds Vercel's serverless limits.

## Option 1: Zeabur (Recommended)
Zeabur is very friendly for Telegram bots and offers a free tier.

1. **Push to GitHub**: Ensure your code is pushed to a GitHub repository.
2. **Login to Zeabur**: Go to [zeabur.com](https://zeabur.com) and login with GitHub.
3. **Create Project**: Create a new project.
4. **Deploy Service**:
   - Click "Deploy New Service".
   - Select "GitHub".
   - Choose your repository.
   - Zeabur will automatically detect the `Dockerfile`.
5. **Configure Variables**:
   - Go to the "Variables" tab of your service.
   - Add the following variables:
     - `TELEGRAM_BOT_TOKEN`: Your bot token
     - `MODELSCOPE_API_KEY`: Your ModelScope API key
     - `ADMIN_ID`: Your Telegram User ID
6. **Done**: Your bot should start automatically.

## Option 2: Railway
Railway is another excellent option for Docker apps.

1. **Login to Railway**: Go to [railway.app](https://railway.app).
2. **New Project**: Click "New Project" -> "Deploy from GitHub repo".
3. **Select Repo**: Choose your repository.
4. **Variables**:
   - Go to the "Variables" tab.
   - Add `TELEGRAM_BOT_TOKEN`, `MODELSCOPE_API_KEY`, and `ADMIN_ID`.
5. **Deploy**: Railway will build and deploy your bot.

## Option 3: Local Docker
You can run the bot locally using Docker Compose.

1. Create a `.env` file with your keys:
   ```bash
   TELEGRAM_BOT_TOKEN=xxx
   MODELSCOPE_API_KEY=xxx
   ADMIN_ID=xxx
   ```
2. Run:
   ```bash
   docker-compose up -d
   ```
