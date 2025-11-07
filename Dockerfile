# Multi-service Docker setup for PE Dashboard
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers in a separate step (faster)
RUN python -m playwright install chromium --no-shell

# Copy source code
COPY src/ ./src/
COPY data/forbes_ai50_seed.json ./data/

# Expose ports for both FastAPI and Streamlit
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "uvicorn", "src.backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
