#requires -Version 5.1
# PharmaVision AI — verified release deployment for Windows Server / NSSM.
# This script keeps the SQLite DB and .env untouched, and never restarts Caddy.
# Run in an elevated PowerShell prompt after pushing changes to GitHub.
$ErrorActionPreference = "Stop"
$site = "C:\web\pharmora"
$python = "C:\Program Files\Python313\python.exe"
$repoZip = "https://github.com/ngochieu1762005/Pharmora-/archive/refs/heads/main.zip"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stage = "C:\web\deploy\$stamp"
$backup = "C:\web\backups\$stamp"
$serviceName = "PharmoraBackend"
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
$wasRunning = [bool]($service -and $service.Status -eq "Running")
$changed = $false
$stopped = $false

if (!(Test-Path $python)) { throw "Python not found: $python" }
if (!(Test-Path $site)) { throw "Site directory not found: $site" }
if (!(Test-Path (Join-Path $site "server.py"))) { throw "Current server.py not found" }

New-Item -ItemType Directory -Force -Path $stage,$backup | Out-Null
Write-Host "1/6 Downloading current GitHub source..." -ForegroundColor Cyan
$zip = Join-Path $stage "main.zip"
Invoke-WebRequest -Uri $repoZip -OutFile $zip
Expand-Archive -Path $zip -DestinationPath (Join-Path $stage "source") -Force
$folder = Get-ChildItem (Join-Path $stage "source") -Directory | Select-Object -First 1
if (!$folder) { throw "Downloaded GitHub ZIP does not contain source" }
$src = $folder.FullName
foreach ($file in @("server.py","test_app.py","static\app.css","tools\build_assets.py")) {
    if (!(Test-Path (Join-Path $src $file))) {
        throw "Missing required source: $file"
    }
}

Write-Host "2/6 Checking asset build and running integration tests..." -ForegroundColor Cyan
Push-Location $src
try {
    & $python "tools\build_assets.py" --check
    if ($LASTEXITCODE -ne 0) { throw "CSS bundle verification failed" }

    & $python -m py_compile server.py test_app.py
    if ($LASTEXITCODE -ne 0) { throw "Python syntax check failed" }

    & $python -m unittest -v test_app.py
    if ($LASTEXITCODE -ne 0) { throw "Integration tests failed. Current site not touched." }
}
finally { Pop-Location }

Write-Host "3/6 Backing up application and SQLite..." -ForegroundColor Cyan
$db = Join-Path $site "pharmavision.sqlite3"
if (Test-Path $db) {
    $dbBackup = Join-Path $backup "pharmavision.sqlite3"
    $backupPython = 'import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()'
    & $python -c $backupPython $db $dbBackup
    if ($LASTEXITCODE -ne 0) { throw "SQLite backup failed. Current site not touched." }
}
Copy-Item (Join-Path $site "server.py") (Join-Path $backup "server.py") -Force
if (Test-Path (Join-Path $site "test_app.py")) {
    Copy-Item (Join-Path $site "test_app.py") (Join-Path $backup "test_app.py") -Force
}
foreach ($directory in @("static","tools")) {
    if (Test-Path (Join-Path $site $directory)) {
        Copy-Item (Join-Path $site $directory) (Join-Path $backup $directory) -Recurse -Force
    }
}

if (!$service) {
    $listener = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
    if ($listener.Count -gt 0) {
        throw "Port 8000 is already in use. Stop the manually started Python server."
    }
}

try {
    Write-Host "4/6 Stopping backend service (if running)..." -ForegroundColor Cyan
    if ($wasRunning) {
        Stop-Service -Name $serviceName -ErrorAction Stop
        (Get-Service -Name $serviceName).WaitForStatus("Stopped",[TimeSpan]::FromSeconds(30))
        $stopped = $true
    }

    Write-Host "5/6 Installing verified application files..." -ForegroundColor Cyan
    $changed = $true
    Copy-Item (Join-Path $src "server.py") (Join-Path $site "server.py") -Force
    Copy-Item (Join-Path $src "test_app.py") (Join-Path $site "test_app.py") -Force

    foreach ($directory in @("static","tools")) {
        $target = Join-Path $site $directory
        if (Test-Path $target) { Remove-Item $target -Recurse -Force }
        Copy-Item (Join-Path $src $directory) $target -Recurse -Force
    }

    # Deliberately preserve pharmavision.sqlite3, .env, files, uploads and sessions.
    Write-Host "6/6 Restarting and checking backend..." -ForegroundColor Cyan
    if ($service) {
        if ($wasRunning) { Start-Service -Name $serviceName -ErrorAction Stop }
        elseif ((Get-Service -Name $serviceName).Status -eq "Stopped") {
            Write-Host "Backend was stopped before deployment; it remains stopped." -ForegroundColor Yellow
        }
    }
    if ($wasRunning) {
        (Get-Service -Name $serviceName).WaitForStatus("Running",[TimeSpan]::FromSeconds(30))
        $healthy = $false
        for ($attempt=0; $attempt -lt 10; $attempt++) {
            try {
                $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/me" -UseBasicParsing -TimeoutSec 5
                if ($r.StatusCode -eq 200) { $healthy = $true; break }
            } catch { Start-Sleep -Seconds 2 }
        }
        if (!$healthy) { throw "Backend health check failed after deployment" }
    }
    Write-Host "DEPLOYED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "Backup: $backup"
    Write-Host "CaddyWeb service was not modified."
}
catch {
    $reason = $_.Exception.Message
    Write-Warning "Deployment error: $reason"
    if ($changed) {
        Write-Warning "Restoring previous application code. SQLite remains unchanged."
        if (Test-Path (Join-Path $backup "server.py")) {
            Copy-Item (Join-Path $backup "server.py") (Join-Path $site "server.py") -Force
        }
        if (Test-Path (Join-Path $backup "test_app.py")) {
            Copy-Item (Join-Path $backup "test_app.py") (Join-Path $site "test_app.py") -Force
        }
        foreach ($directory in @("static","tools")) {
            $sourceBackup = Join-Path $backup $directory
            $target = Join-Path $site $directory
            if (Test-Path $sourceBackup) {
                if (Test-Path $target) { Remove-Item $target -Recurse -Force }
                Copy-Item $sourceBackup $target -Recurse -Force
            }
        }
    }
    if ($wasRunning) {
        try {
            if ((Get-Service -Name $serviceName).Status -eq "Running") {
                Restart-Service -Name $serviceName -ErrorAction Stop
            } else {
                Start-Service -Name $serviceName -ErrorAction Stop
            }
            Write-Host "Previous backend code has been restarted." -ForegroundColor Yellow
        } catch {
            Write-Warning "Service recovery failed: $($_.Exception.Message). Check service logs and backup."
        }
    }
    throw "Deployment aborted: $reason. Backup: $backup"
}
