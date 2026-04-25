FROM python:3.12-slim-bookworm

WORKDIR /workspace

# Copy benchmark content and reference databases
COPY data/ /workspace/data/
COPY task_data/ /workspace/task_data/

# Install minimal dependencies
RUN pip install --no-cache-dir inspect-ai

# Copy source
COPY src/ /workspace/src/
COPY pyproject.toml /workspace/

# Install the package
RUN pip install --no-cache-dir -e .

CMD ["tail", "-f", "/dev/null"]
