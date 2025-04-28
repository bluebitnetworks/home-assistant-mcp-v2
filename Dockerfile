# Dockerfile for Home Assistant MCP backend
FROM python:3.8-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/

# Default command
CMD ["python", "src/main.py"]
