# Use Python 3.12 slim image for production
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Install system dependencies including cron and sudo
RUN apt-get update && apt-get install -y \
    gcc \
    cron \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create apk_files directory
RUN mkdir -p /app/apk_files

# Create startup script
COPY start_with_cron_fixed.sh /app/start_with_cron.sh
RUN chmod +x /app/start_with_cron.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    echo "app ALL=(ALL) NOPASSWD: /usr/sbin/service, /usr/sbin/cron, /bin/systemctl, /usr/sbin/cron" >> /etc/sudoers

# Create cron job for root user (cron needs to run as root)
RUN echo "*/5 * * * * cd /app && /usr/local/bin/python3 check_expired_keys.py >> /app/cronjob.log 2>&1" > /etc/cron.d/vpn-bot && \
    chmod 0644 /etc/cron.d/vpn-bot

# Create logs directory
RUN mkdir -p /app/logs && chown -R app:app /app/logs

# Switch to app user
USER app

# Expose ports (Flask web admin runs on 5000)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py

# Run the application with cron
CMD ["/app/start_with_cron.sh"]
