$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$runtime = 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies'
$env:RUNTIME_NODE_MODULES = Join-Path $runtime 'node\node_modules'
$env:RUNTIME_NODE = Join-Path $runtime 'node\bin\node.exe'
$env:RUNTIME_PYTHON = Join-Path $runtime 'python\python.exe'
if (-not (Test-Path $env:RUNTIME_NODE)) { throw 'Bundled presentation Node runtime is unavailable; update the runtime path in rebuild.ps1.' }
Push-Location $repo
try {
    & $env:RUNTIME_NODE (Join-Path $PSScriptRoot 'build_presentation.mjs')
    if ($LASTEXITCODE -ne 0) { throw 'PowerPoint build failed.' }
    & $env:RUNTIME_PYTHON (Join-Path $PSScriptRoot 'export_pdf.py')
    if ($LASTEXITCODE -ne 0) { throw 'PDF export failed.' }
} finally { Pop-Location }
