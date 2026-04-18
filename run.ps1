$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path -Path $VenvDir -PathType Container)) {
    if ($env:PYTHON_BIN) {
        & $env:PYTHON_BIN -m venv $VenvDir
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $VenvDir
    }
    else {
        & python -m venv $VenvDir
    }
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $RootDir "requirements.txt")
& $VenvPython (Join-Path $RootDir "dct-jpeg.py") @args
