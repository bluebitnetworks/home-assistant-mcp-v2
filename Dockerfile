# Dockerfile for Home Assistant MCP backend
FROM python:3.8-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
COPY setup.py ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e .

# Copy all source code and config files
COPY src/ src/
COPY config.yaml* ./
COPY .env.example ./
COPY mcp_schemas.json ./
COPY README* ./

# Expose the default port (Fly.io uses $PORT, default to 8080)
EXPOSE 8080

# Default command: Run FastAPI app with uvicorn
CMD ["uvicorn", "src.web_api_v3:app", "--host", "0.0.0.0", "--port", "8080"]
