FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ /app/src/
ENV PYTHONPATH="/app/src:${PYTHONPATH}"
ENV PORT=8080
ENV HOST=0.0.0.0
ENV SECRET_STORE_BACKEND=k3s

# Create non-root user
RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "tag_validator.api.app:create_app()"]
