# ATU Studio dashboard launcher
param([switch]$NoBrowser)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "                         ATU Studio Dashboard" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "`nStarting the dashboard, or opening it if it is already running...`n" -ForegroundColor Gray

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$ServerArguments = @('-u', (Join-Path $ScriptDir 'serve_frontend.py'))
if ($NoBrowser) { $ServerArguments += '--no-browser' }
$DashboardExit = 1
Push-Location -LiteralPath $ScriptDir
try {
    if (Test-Path -LiteralPath $VenvPython) {
        & $VenvPython @ServerArguments
    } else {
        python @ServerArguments
    }
    if ($null -ne $LASTEXITCODE) { $DashboardExit = $LASTEXITCODE }
} catch {
    Write-Host "The dashboard could not start: $_" -ForegroundColor Red
} finally {
    Pop-Location
}
exit $DashboardExit
