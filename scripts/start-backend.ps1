$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$CheckScript = Join-Path $ProjectRoot "scripts\check-python-env.py"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Error "Project Python not found: $PythonExe"
    exit 1
}

$PreviousPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$PreviousPythonHome = [Environment]::GetEnvironmentVariable("PYTHONHOME", "Process")
$HadPythonPath = $null -ne $PreviousPythonPath
$HadPythonHome = $null -ne $PreviousPythonHome
$ExitCode = 0

Push-Location $ProjectRoot
try {
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "Process")
    [Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "Process")

    & $PythonExe $CheckScript
    $ExitCode = $LASTEXITCODE

    if ($ExitCode -eq 0) {
        & $PythonExe -m uvicorn main:app --reload
        $ExitCode = $LASTEXITCODE
    }
}
finally {
    if ($HadPythonPath) {
        [Environment]::SetEnvironmentVariable("PYTHONPATH", $PreviousPythonPath, "Process")
    }
    else {
        [Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "Process")
    }

    if ($HadPythonHome) {
        [Environment]::SetEnvironmentVariable("PYTHONHOME", $PreviousPythonHome, "Process")
    }
    else {
        [Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "Process")
    }

    Pop-Location
}

exit $ExitCode
