#requires -version 5.1
# Safe ZIP-based update for the local MVP on Windows Server (Git not required).
# Run as Administrator AFTER stopping the interactive Python server.
$ErrorActionPreference = 'Stop'
$site = 'C:\web\pharmora'
$python = 'C:\Program Files\Python313\python.exe'
$repoZip = 'https://github.com/ngochieu1762005/Pharmora-/archive/refs/heads/main.zip'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stage = "C:\web\deploy\$stamp"
$backup = "C:\web\backups\$stamp"
if (!(Test-Path $python)) { throw "Python not found: $python" }
if (!(Test-Path $site)) { throw "Site not found: $site" }
# Do not overwrite code while a manually launched process is serving requests.
$livePort = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($livePort.Count) {
  throw 'Port 8000 is listening. Stop Pharmora server with Ctrl+C before deploying.'
}
New-Item -ItemType Directory -Force $stage,$backup | Out-Null
$zip = Join-Path $stage 'main.zip'
Invoke-WebRequest -Uri $repoZip -OutFile $zip
Expand-Archive -Path $zip -DestinationPath (Join-Path $stage 'source') -Force
$source = Get-ChildItem (Join-Path $stage 'source') -Directory | Select-Object -First 1
if (!$source) { throw 'Extracted archive has no source directory.' }
$src = $source.FullName
if (!(Test-Path (Join-Path $src 'server.py'))) { throw 'Archive missing server.py.' }
Push-Location $src
try {
  & $python -m unittest -v test_app.py
  if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed. Deployment canceled.' }
} finally { Pop-Location }
# SQLite backup API gives a consistent snapshot even with WAL mode.
$db = Join-Path $site 'pharmavision.sqlite3'
if (Test-Path $db) {
  $dbBackup = Join-Path $backup 'pharmavision.sqlite3'
  $script = 'import sqlite3,sys; src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()'
  & $python -c $script $db $dbBackup
  if ($LASTEXITCODE -ne 0) { throw 'SQLite backup failed; deployment canceled.' }
}
Copy-Item -Path (Join-Path $site 'server.py') -Destination $backup -Force
if (Test-Path (Join-Path $site 'static')) {
  Copy-Item -Path (Join-Path $site 'static') -Destination (Join-Path $backup 'static') -Recurse -Force
}
# Whitelist the application files; never overwrite SQLite, uploads or .env.
Copy-Item (Join-Path $src 'server.py') $site -Force
Copy-Item (Join-Path $src 'test_app.py') $site -Force
if (Test-Path (Join-Path $site 'static')) { Remove-Item (Join-Path $site 'static') -Recurse -Force }
Copy-Item (Join-Path $src 'static') (Join-Path $site 'static') -Recurse -Force
Write-Host "Updated from GitHub. Backup: $backup" -ForegroundColor Green
Write-Host 'Restart the Python server. Caddy need not be restarted for code-only changes.'
