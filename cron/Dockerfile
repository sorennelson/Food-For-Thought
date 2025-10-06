FROM python:3.11-slim

# Install cron
RUN apt-get update && apt-get install -y curl cron && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY scripts/ ./scripts/
COPY crontab /etc/cron.d/my-cron
COPY start_cron.sh .

# Give execution rights
RUN chmod 0644 /etc/cron.d/my-cron
RUN chmod +x ./start_cron.sh

# Apply cron job
RUN crontab /etc/cron.d/my-cron

# Create logs folder
RUN mkdir -p /app/logs

# Expose logs as volume (optional)
VOLUME ["/app/logs"]

# Run cron in foreground
CMD ["./start_cron.sh"]
# CMD ["cron", "-f"]