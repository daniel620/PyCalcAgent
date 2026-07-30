FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy project configuration and dependencies
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/

# Install the package and dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir -r requirements.txt

# Default command to run the interactive CLI
ENTRYPOINT ["python", "-m", "pycalcagent.cli"]
CMD ["--help"]
