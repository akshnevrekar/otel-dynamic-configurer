FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install fastapi uvicorn pyyaml

# Install system dependencies
RUN apt-get update && \
    apt-get install -y procps curl && \
    rm -rf /var/lib/apt/lists/*

# Download and install otelcol-contrib
ENV OTELCOL_VERSION=0.130.1
RUN curl -LO https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${OTELCOL_VERSION}/otelcol-contrib_${OTELCOL_VERSION}_linux_amd64.tar.gz && \
    tar -xzf otelcol-contrib_${OTELCOL_VERSION}_linux_amd64.tar.gz && \
    mv otelcol-contrib /usr/local/bin/otelcol-contrib && \
    chmod +x /usr/local/bin/otelcol-contrib && \
    rm otelcol-contrib_${OTELCOL_VERSION}_linux_amd64.tar.gz

COPY init_container.sh /init_container.sh
RUN chmod +x /init_container.sh

# Copy your FastAPI app
COPY main.py /app

# Expose FastAPI port
EXPOSE 8000

# Default command runs FastAPI only
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
