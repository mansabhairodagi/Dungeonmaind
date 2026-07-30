# One-command Docker startup for Dungeon M-AI-nd (frontend + backend + Ollama).
# Usage: .\start-docker.ps1 [-Detached]

param(
    [switch]$Detached
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
}

try {
    docker info | Out-Null
} catch {
    Write-Error "Docker daemon is not running. Start Docker Desktop and try again."
}

if (-not (Test-Path '.\backend\.env')) {
    Copy-Item '.\backend\.env.example' '.\backend\.env'
    Write-Host 'Created backend\.env from .env.example — edit HF_TOKEN or OLLAMA_API_KEY if needed.'
}

Write-Host 'Starting Dungeon M-AI-nd with Docker Compose...'
Write-Host '  Frontend: http://localhost:5173'
Write-Host '  Backend:  http://localhost:8000'
Write-Host '  Ollama:   http://localhost:11434'
Write-Host ''

$composeArgs = @('compose', 'up', '--build')
if ($Detached) {
    $composeArgs += '-d'
}

& docker @composeArgs @args
