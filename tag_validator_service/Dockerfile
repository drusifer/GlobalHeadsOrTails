FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    PORT=8080 \
    HOST=0.0.0.0 \
    SECRET_STORE_BACKEND=k3s

WORKDIR /app

# Copy package metadata and source code
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

# Install package with k3s secret store and gunicorn WSGI server extras, and verify dependency tree
RUN pip install --no-cache-dir ".[k3s,server]" && pip check

# Create non-root user matching k8s deployment securityContext (uid 10001)
RUN useradd -u 10001 -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-tmp-dir", "/tmp", "--access-logfile", "-", "tag_validator.api.app:create_app()"]
