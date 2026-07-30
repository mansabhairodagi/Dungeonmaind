#!/bin/sh

# Ensure the .env file for the backend exists
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file for backend from .env.example..."
    cp "backend/.env.example" "backend/.env"
fi

echo "Building and starting Docker containers in the background..."
docker compose up --build -d

echo "
Application is running.
You can view logs with: docker compose logs -f
To stop the application, run: docker compose down"