# Ensure the .env file for the backend exists
if (-not (Test-Path "backend/.env")) {
    Write-Host "Creating .env file for backend from .env.example..."
    Copy-Item "backend/.env.example" "backend/.env"
}

Write-Host "Building and starting Docker containers in the background..."
docker compose up --build -d

Write-Host "
Application is running.
You can view logs with: docker compose logs -f
To stop the application, run: docker compose down"