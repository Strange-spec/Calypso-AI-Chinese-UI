# ==========================================
# Stage 1: Frontend Build (Node.js 20 Alpine)
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy package manifests first for efficient Docker layer caching
COPY web/package*.json ./

# Install frontend dependencies
RUN npm ci || npm install

# Copy frontend source code and compile production assets
COPY web/ ./
RUN npm run build

# ==========================================
# Stage 2: Runtime Runner (Python 3.11 Slim)
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_MODE=demo \
    PORT=8080

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY app/ ./app/

# Copy compiled frontend static bundle from frontend-builder stage
COPY --from=frontend-builder /build/dist ./app/static

# Expose application port
EXPOSE 8080

# Container healthcheck targeting the system status API
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/system/status || exit 1

# Run FastAPI backend via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
