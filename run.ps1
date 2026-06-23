<#
  Verified Recovery Agent — one-command runner (Windows / PowerShell).

  Usage:   ./run.ps1 <command>
  Commands:
    install   Install backend (editable + dev) and frontend dependencies
    dev       Start backend (:8000, hot-reload) AND frontend (:3000, hot-reload) together
    backend   Start only the backend (hot-reload)
    frontend  Start only the frontend (hot-reload)
    seed      Load the synthetic Northstar plant + scenario (idempotent)
    reset     Wipe + reseed the database
    demo      Run the full PO-2841 recovery replay headless
    eval      Agent reliability eval (proves it never false-closes a relapse)
    test      Run backend (pytest) and frontend (vitest) test suites

  Notes: dev mode uses `next dev` so source edits hot-reload. (`npm start` serves a
  production build and will NOT reflect edits without a rebuild.)
#>
param([Parameter(Position = 0)][string]$cmd = "dev")

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"

function Backend-Uvicorn {
  Push-Location $backend
  try { & $py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 } finally { Pop-Location }
}

switch ($cmd) {
  "install" {
    Push-Location $backend; & $py -m pip install -e ".[dev]"; Pop-Location
    Push-Location $frontend; npm install; Pop-Location
  }
  "seed"  { Push-Location $backend; & $py -m app.cli seed;  Pop-Location }
  "reset" { Push-Location $backend; & $py -m app.cli reset; Pop-Location }
  "demo"  { Push-Location $backend; & $py -m app.cli demo;  Pop-Location }
  "eval"  { Push-Location $backend; & $py -m app.cli eval;  Pop-Location }
  "test"  {
    Push-Location $backend; & $py -m pytest; Pop-Location
    Push-Location $frontend; npm test; Pop-Location
  }
  "backend"  { Backend-Uvicorn }
  "frontend" { Push-Location $frontend; npm run dev; Pop-Location }
  "dev" {
    Write-Host "Starting backend (:8000) in a new window and frontend (:3000) here..." -ForegroundColor Cyan
    Start-Process -FilePath $py `
      -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" `
      -WorkingDirectory $backend
    Push-Location $frontend; npm run dev; Pop-Location
  }
  default { Write-Host "Unknown command '$cmd'. Use: install|dev|backend|frontend|seed|reset|demo|eval|test" }
}
