project/
│
├── app.py               # Main Python file with FastAPI and Selenium logic
├── config.json          # Configuration file (stores login, password, URLs, etc.)
├── Dockerfile           # Dockerfile to build the Docker image
├── requirements.txt     # Python dependencies

How to Build and Run the Docker Container:

Build the Docker Image:
docker build -t selenium-chromium-app .

Run the Docker Container:

docker run -d -p 8000:8000 -v $(pwd):/usr/src/app selenium-chromium-app
