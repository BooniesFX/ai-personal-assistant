# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed for Pillow/etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (including dev dependencies for now)
RUN uv sync --frozen

# Copy application code
COPY . .

# Create volume directory for data
RUN mkdir -p data

# Run the bot using uv run (which activates the venv automatically)
CMD ["uv", "run", "telegram_bot.py"]
