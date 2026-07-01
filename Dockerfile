# Use the official Python lightweight image
FROM python:3.13-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the project into /app
COPY . /app
WORKDIR /app

# Ensure logs output instantly
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN uv sync

# Optional: Hardcode to 8080 for local testing documentation (Cloud Run ignores EXPOSE)
EXPOSE 8080

# Start the server 
CMD ["uv", "run", "server.py"]