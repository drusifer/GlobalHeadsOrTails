# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN useradd -m appuser

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install the package dependencies and Gunicorn
RUN pip install --no-cache-dir .[server] gunicorn

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port
EXPOSE 8000

# Run Gunicorn pointing to the app module defined in Makefile
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "ntag424_sdm_provisioner.server.app:app"]