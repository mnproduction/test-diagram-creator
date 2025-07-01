# Based on the official example from https://github.com/astral-sh/uv-docker-example

# Stage 1: Build the virtual environment using an official uv image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set recommended uv environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Ensure uv uses the python from this image, not one it downloads
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies into a new virtual environment.
# This is cached and will only be re-run when dependency files change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project

# Copy the project definition files
COPY pyproject.toml uv.lock README.md ./

# Copy the rest of the application source code
COPY ./src ./src
COPY ./utils ./utils
COPY ./main.py .

# Install the project itself into the venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked


# Stage 2: Create the final, lean image
FROM python:3.12-slim-bookworm AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies including graphviz
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user before copying files
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Copy the application and the populated venv from the builder stage
COPY --from=builder --chown=appuser:appgroup /app /app

# Set the working directory
WORKDIR /app

# Set the PATH to include the venv's bin directory
ENV PATH="/app/.venv/bin:$PATH"

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Set the command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]