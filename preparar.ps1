param(
    [ValidateSet('preparar','iniciar','equipo','doctor','terminal','notas')][string]$Accion = 'preparar',
    [switch]$SoloDetectar,
    [switch]$SinOpenCode,
    [switch]$SinCalibrar,
    [switch]$SinObsidian,
    [ValidateSet('auto','si','no','elegir')][string]$UI = 'auto'
)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskTools = Join-Path $taskRoot '.tools\uv'
$taskUv = Join-Path $taskTools 'uv.exe'
if (-not (Test-Path -LiteralPath $taskUv)) {
    New-Item -ItemType Directory -Path $taskTools -Force | Out-Null
    $taskArchitecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
    $taskArchiveName = "uv-$taskArchitecture-pc-windows-msvc.zip"
    $taskBase = 'https://github.com/astral-sh/uv/releases/download/0.13.9/'
    $taskArchive = Join-Path $taskTools $taskArchiveName
    Write-Host 'Descargando uv para preparar Python sin cambiar el PATH...'
    Invoke-WebRequest -UseBasicParsing -Uri ($taskBase + $taskArchiveName) -OutFile $taskArchive
    $taskHash = (Invoke-WebRequest -UseBasicParsing -Uri ($taskBase + $taskArchiveName + '.sha256')).Content
    if ($taskHash -is [byte[]]) { $taskHash = [Text.Encoding]::UTF8.GetString($taskHash) }
    $taskExpectedHash = ([string]$taskHash).Trim().Split(' ')[0]
    if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpectedHash.ToLowerInvariant()) {
        throw 'La descarga de uv no coincide con su checksum oficial.'
    }
    Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskTools -Force
}
Push-Location -LiteralPath $taskRoot
try {
    $taskArguments = @('run','--python','3.11','--extra','mcp','herramientas/entorno.py',$Accion)
    if ($SoloDetectar) { $taskArguments += '--solo-detectar' }
    if ($SinOpenCode) { $taskArguments += '--sin-opencode' }
    if ($SinCalibrar) { $taskArguments += '--sin-calibrar' }
    if ($SinObsidian) { $taskArguments += '--sin-obsidian' }
    $taskArguments += @('--ui', $UI)
    & $taskUv @taskArguments
    if ($LASTEXITCODE -ne 0) { throw "La preparación terminó con código $LASTEXITCODE. Revisa el mensaje anterior." }
} finally {
    Pop-Location
}
