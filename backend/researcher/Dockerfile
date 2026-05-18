FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright system deps and Chromium
RUN npx -y playwright install --with-deps chromium

# Install @playwright/mcp locally so the binary is at a known path (/app/node_modules/.bin/)
RUN npm install @playwright/mcp@latest

# Install Python package manager
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./

# Install Python dependencies during build
RUN uv sync --frozen --no-install-project

# Copy application code
COPY *.py ./

# Use venv Python directly to avoid uv filesystem writes at Lambda invocation time
ENTRYPOINT ["/app/.venv/bin/python", "-m", "awslambdaric"]
CMD ["server.handler"]