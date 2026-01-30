FROM python:3.13-slim

# Install system dependencies for Playwright and PDF processing
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install the project
COPY . .
RUN pip install --no-cache-dir .

# Install Playwright browser binaries
RUN playwright install chromium

# Default environment variable pointing to the internal SearxNG container
ENV SEARXNG_HOST=http://searxng:8080

# Expose MCP port (if running as server)
EXPOSE 8000

ENTRYPOINT ["websearx-server"]