# Use Debian Buster slim as the base image for better compatibility with Chrome dependencies
FROM debian:buster-slim

# Install system dependencies, Python 3, and pip
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg2 \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxrandr2 \
    libasound2 \
    xdg-utils \
    libdrm2 \
    libgbm1 \
    libu2f-udev \
    libvulkan1 \
    python3 \
    python3-pip \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Download and install Google Chrome version 114 from the mirror
RUN wget -q https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.90-1_amd64.deb && \
    apt-get install -y ./google-chrome-stable_114.0.5735.90-1_amd64.deb && \
    rm google-chrome-stable_114.0.5735.90-1_amd64.deb

# Install ChromeDriver version 114 to match Chrome
RUN wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# Set display port for headless Chrome
ENV DISPLAY=:99

# Create working directory
WORKDIR /usr/src/app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the FastAPI default port
EXPOSE 8000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
