# PowerShell script to start the backend server
Write-Host "🚀 Starting Payment Gateway Backend..." -ForegroundColor Green

# Change to backend directory
Set-Location -Path "backend"

# Start the FastAPI server
Write-Host "📡 Starting server on http://localhost:8000" -ForegroundColor Yellow
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 