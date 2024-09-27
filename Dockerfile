# Use Debian Buster for better compatibility with Chrome dependencies
FROM debian:buster-slim

# Install system dependencies, Python 3, pip, and build tools for cryptography
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libxss1 \
    libgtk-3-0 \
    fonts-liberation \
    libgbm1 \
    libvulkan1 \
    xdg-utils \
    apt-utils \
    python3 \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Set environment variable to prevent pip from building from source
ENV PIP_NO_BINARY=cryptography

# Download and install Google Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# Set display port for headless mode
ENV DISPLAY=:99

# Create working directory
WORKDIR /usr/src/app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the FastAPI default port
EXPOSE 8000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
