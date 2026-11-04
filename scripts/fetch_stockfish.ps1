$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $root "bin"
$tag = "sf_19"
$asset = "stockfish-windows-x86-64-universal.zip"
$url = "https://github.com/official-stockfish/Stockfish/releases/download/$tag/$asset"
$work = Join-Path ([IO.Path]::GetTempPath()) ("stockfish-" + [Guid]::NewGuid())
New-Item -ItemType Directory -Force $bin, $work | Out-Null
try {
    $zip = Join-Path $work $asset
    Invoke-WebRequest $url -OutFile $zip
    Expand-Archive $zip (Join-Path $work "x") -Force
    $exe = Get-ChildItem (Join-Path $work "x") -Recurse -Filter "stockfish-*.exe" | Select-Object -First 1
    Copy-Item $exe.FullName (Join-Path $bin "stockfish.exe") -Force
    Write-Host "Stockfish $tag instalado em $bin"
}
finally {
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
}
