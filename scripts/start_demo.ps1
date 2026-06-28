$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PortableNode = "C:\Users\Administrator\Documents\Codex\2026-06-05\i-have-a-streamlit-project-called\work\node-v20.11.1-win-x64"

function Stop-PortProcess {
    param([int]$Port)

    $lines = netstat -ano | Select-String ":$Port"
    foreach ($line in $lines) {
        $parts = $line.ToString() -split "\s+"
        $procId = [int]$parts[-1]
        if ($procId -ne 0) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

Stop-PortProcess -Port 8501
Stop-PortProcess -Port 3000

Start-Process `
    -FilePath "$ProjectRoot\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

Start-Process `
    -FilePath "$PortableNode\npm.cmd" `
    -ArgumentList "run", "dev", "--", "-p", "3000" `
    -WorkingDirectory "$ProjectRoot\dentpilot-oral-app" `
    -WindowStyle Hidden

Start-Sleep -Seconds 6

Write-Host "DentPilot AI main app:       http://localhost:8501"
Write-Host "Realtime oral exam app:      http://localhost:3000"
