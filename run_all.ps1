# ── Facial Expression Platform — Launcher ──
# Runs everything with just 2 terminals (backend + frontend)

$projectRoot = $PSScriptRoot

# 1. Start Redis
Write-Host "`n[1/3] Starting Redis..." -ForegroundColor Cyan
docker compose -f "$projectRoot\docker-compose.yml" up -d redis
Start-Sleep -Seconds 2

# 2. Start ALL backend services in one process
Write-Host "`n[2/3] Starting Backend (all services in one process)..." -ForegroundColor Yellow
$env:PYTHONPATH = $projectRoot
Start-Process -FilePath "$projectRoot\venv\Scripts\python.exe" -ArgumentList "$projectRoot\backend\run_all_services.py" -WorkingDirectory $projectRoot

# 3. Start Angular Frontend
Write-Host "`n[3/3] Starting Angular Frontend..." -ForegroundColor Green
Start-Process -FilePath "npx" -ArgumentList "ng serve --open" -WorkingDirectory "$projectRoot\frontend"

Write-Host "`n All services launched!" -ForegroundColor Magenta
Write-Host "   Backend API Gateway:  http://localhost:8000" -ForegroundColor White
Write-Host "   Frontend Dashboard:   http://localhost:4200" -ForegroundColor White
Write-Host "`n   Press Ctrl+C in the backend window to stop services.`n" -ForegroundColor DarkGray
