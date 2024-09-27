# Use Python 3.10-slim as the base image
FROM python:3.10-slim

# Install system dependencies, wget, gnupg, and other required libraries
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    unzip \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxrandr2 \
    libasound2 \
    xdg-utils \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Download Chrome 114 and install it
RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.90-1_amd64.deb && \
    apt-get install -y ./google-chrome-stable_114.0.5735.90-1_amd64.deb && \
    rm google-chrome-stable_114.0.5735.90-1_amd64.deb

# Install ChromeDriver version 114
RUN wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip

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
