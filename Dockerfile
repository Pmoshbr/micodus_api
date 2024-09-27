# Use Python 3.10-slim as the base image
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils

# Install system dependencies, Chrome, and ChromeDriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxkbcommon0 \
    libxcomposite1 \
    libxrandr2 \
    libasound2 \
    libxss1 \
    xdg-utils \
    # Chrome dependencies
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    # Download and install ChromeDriver
    && CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip \
    # Cleanup
    && apt-get remove -y wget unzip curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set the working directory
WORKDIR /usr/src/app

# Copy the rest of the application code
COPY . .

# Set display port for headless Chrome
ENV DISPLAY=:99

# Expose the FastAPI default port
EXPOSE 8000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
