FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy CORTEX core package
COPY cortex-memory/cortex/ ./cortex/
COPY cortex-memory/setup.py ./
COPY cortex-memory/pyproject.toml ./

# Install CORTEX as a package
RUN pip install -e .

# Copy server code
COPY server/ ./server/
COPY server/requirements.txt ./requirements-server.txt
RUN pip install -r requirements-server.txt

# Create data directory
RUN mkdir -p /app/data /app/vault

EXPOSE 8900

CMD ["uvicorn", "server.cortex_server:app", "--host", "0.0.0.0", "--port", "8900"]
