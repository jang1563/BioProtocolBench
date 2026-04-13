FROM python:3.12-slim-bookworm

WORKDIR /workspace

# Copy reference databases
COPY data/ /workspace/data/

# Copy protocols
COPY protocols/ /workspace/protocols/

# Install minimal dependencies
RUN pip install --no-cache-dir inspect-ai

# Copy source
COPY src/ /workspace/src/
COPY pyproject.toml /workspace/

# Install the package
RUN pip install --no-cache-dir -e .

CMD ["tail", "-f", "/dev/null"]
